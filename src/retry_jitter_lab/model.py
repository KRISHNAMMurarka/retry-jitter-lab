"""Discrete-event retry simulator and backoff strategies."""

from __future__ import annotations

import heapq
import math
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Strategy(str, Enum):
    """Supported retry-delay strategies."""

    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Configuration for one retry simulation.

    ``max_retries`` counts retries after the initial request, so each client can
    make at most ``max_retries + 1`` attempts.
    """

    clients: int = 600
    capacity_per_second: float = 120.0
    outage_start: float = 1.0
    outage_duration: float = 3.0
    initial_spread: float = 0.4
    base_delay: float = 0.5
    multiplier: float = 2.0
    max_delay: float = 30.0
    max_retries: int = 6
    bucket_width: float = 0.1
    end_time: float = 40.0
    seed: int = 20260812

    def __post_init__(self) -> None:
        numeric_values = (
            self.capacity_per_second,
            self.outage_start,
            self.outage_duration,
            self.initial_spread,
            self.base_delay,
            self.multiplier,
            self.max_delay,
            self.bucket_width,
            self.end_time,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise ValueError("simulation parameters must be finite numbers")
        if not 1 <= self.clients <= 100_000:
            raise ValueError("clients must be between 1 and 100,000")
        if self.capacity_per_second <= 0:
            raise ValueError("capacity_per_second must be greater than zero")
        if self.outage_start < 0:
            raise ValueError("outage_start must not be negative")
        if self.outage_duration < 0:
            raise ValueError("outage_duration must not be negative")
        if self.initial_spread < 0:
            raise ValueError("initial_spread must not be negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be greater than zero")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least one")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be at least base_delay")
        if not 0 <= self.max_retries <= 100:
            raise ValueError("max_retries must be between 0 and 100")
        if self.bucket_width <= 0:
            raise ValueError("bucket_width must be greater than zero")
        if self.end_time <= self.outage_start:
            raise ValueError("end_time must be greater than outage_start")
        if self.bucket_count > 1_000_000:
            raise ValueError("simulation horizon must not exceed 1,000,000 buckets")
        if self.capacity_per_bucket < 1:
            raise ValueError(
                "capacity_per_second * bucket_width must allow at least one "
                "request per bucket"
            )

    @property
    def recovery_time(self) -> float:
        """Time at which the simulated outage ends."""

        return self.outage_start + self.outage_duration

    @property
    def capacity_per_bucket(self) -> int:
        """Whole requests that can be served in one time bucket."""

        return math.floor(self.capacity_per_second * self.bucket_width + 1e-12)

    @property
    def bucket_count(self) -> int:
        """Number of buckets in the simulation horizon."""

        return math.ceil(self.end_time / self.bucket_width)

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable configuration mapping."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class BucketRecord:
    """Observed load and outcomes for one time bucket."""

    index: int
    start_seconds: float
    end_seconds: float
    offered: int
    served: int
    rejected_outage: int
    rejected_overload: int

    @property
    def rejected(self) -> int:
        """Total rejected requests in this bucket."""

        return self.rejected_outage + self.rejected_overload

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable bucket mapping."""

        return {
            "index": self.index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "offered": self.offered,
            "served": self.served,
            "rejected": self.rejected,
            "rejected_outage": self.rejected_outage,
            "rejected_overload": self.rejected_overload,
        }


@dataclass(frozen=True, slots=True)
class SimulationSummary:
    """Aggregate outcomes for one strategy."""

    clients: int
    completed: int
    exhausted: int
    timed_out: int
    attempts: int
    peak_offered_per_second: float
    peak_capacity_ratio: float
    peak_recovery_offered_per_second: float
    peak_recovery_capacity_ratio: float
    last_completion_seconds: float | None
    drain_after_recovery_seconds: float | None

    @property
    def attempts_per_client(self) -> float:
        """Mean number of attempts made per client."""

        return self.attempts / self.clients

    def to_dict(self) -> dict[str, int | float | None]:
        """Return a JSON-serializable summary mapping."""

        return {
            **asdict(self),
            "attempts_per_client": self.attempts_per_client,
        }


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Complete output for one strategy."""

    strategy: Strategy
    summary: SimulationSummary
    buckets: tuple[BucketRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result mapping."""

        return {
            "strategy": self.strategy.value,
            "summary": self.summary.to_dict(),
            "buckets": [bucket.to_dict() for bucket in self.buckets],
        }


def retry_delay(
    strategy: Strategy,
    *,
    retry_index: int,
    rng: random.Random,
    base_delay: float,
    multiplier: float,
    max_delay: float,
    previous_delay: float | None = None,
) -> tuple[float, float]:
    """Calculate the next delay and strategy state.

    ``retry_index`` is zero for the first retry. The returned state is passed
    back as ``previous_delay`` for decorrelated jitter.
    """

    if retry_index < 0:
        raise ValueError("retry_index must not be negative")
    if not all(math.isfinite(value) for value in (base_delay, multiplier, max_delay)):
        raise ValueError("backoff parameters must be finite numbers")
    if base_delay <= 0 or multiplier < 1 or max_delay < base_delay:
        raise ValueError("invalid backoff parameters")

    try:
        exponential = base_delay * multiplier**retry_index
    except OverflowError:
        exponential = math.inf
    capped_exponential = min(max_delay, exponential)

    if strategy is Strategy.NONE:
        delay = capped_exponential
    elif strategy is Strategy.FULL:
        delay = rng.uniform(0.0, capped_exponential)
    elif strategy is Strategy.EQUAL:
        half = capped_exponential / 2.0
        delay = half + rng.uniform(0.0, half)
    elif strategy is Strategy.DECORRELATED:
        prior = previous_delay if previous_delay is not None else base_delay
        upper = min(max_delay, max(base_delay, prior * 3.0))
        delay = rng.uniform(base_delay, upper)
    else:  # pragma: no cover - Enum makes this unreachable to typed callers.
        raise ValueError(f"unsupported strategy: {strategy}")

    return delay, delay


def _strategy_rng(seed: int, strategy: Strategy, client_id: int) -> random.Random:
    """Create a stable, independent retry stream for one client."""

    material = f"retry-jitter-lab-v1:{seed}:{strategy.value}:{client_id}"
    return random.Random(material)


def simulate(config: SimulationConfig, strategy: Strategy) -> SimulationResult:
    """Run a deterministic discrete-event simulation for one strategy."""

    offered = [0] * config.bucket_count
    served = [0] * config.bucket_count
    rejected_outage = [0] * config.bucket_count
    rejected_overload = [0] * config.bucket_count
    offered_after_recovery = [0] * config.bucket_count

    initial_rng = random.Random(config.seed)
    events: list[tuple[float, int, int, int, float | None]] = []
    sequence = 0
    for client_id in range(config.clients):
        offset = initial_rng.uniform(0.0, config.initial_spread)
        events.append((config.outage_start + offset, sequence, client_id, 0, None))
        sequence += 1
    heapq.heapify(events)

    retry_rngs = [
        _strategy_rng(config.seed, strategy, client_id)
        for client_id in range(config.clients)
    ]
    completed = 0
    exhausted = 0
    timed_out = 0
    attempts = 0
    completion_times: list[float] = []

    while events:
        event_time, _, client_id, retry_index, previous_delay = heapq.heappop(events)
        if event_time >= config.end_time:
            timed_out += 1
            continue

        bucket_index = min(
            int(event_time / config.bucket_width),
            config.bucket_count - 1,
        )
        offered[bucket_index] += 1
        if event_time >= config.recovery_time:
            offered_after_recovery[bucket_index] += 1
        attempts += 1

        during_outage = config.outage_start <= event_time < config.recovery_time
        over_capacity = served[bucket_index] >= config.capacity_per_bucket

        if during_outage or over_capacity:
            if during_outage:
                rejected_outage[bucket_index] += 1
            else:
                rejected_overload[bucket_index] += 1

            if retry_index < config.max_retries:
                delay, next_previous = retry_delay(
                    strategy,
                    retry_index=retry_index,
                    rng=retry_rngs[client_id],
                    base_delay=config.base_delay,
                    multiplier=config.multiplier,
                    max_delay=config.max_delay,
                    previous_delay=previous_delay,
                )
                heapq.heappush(
                    events,
                    (
                        event_time + delay,
                        sequence,
                        client_id,
                        retry_index + 1,
                        next_previous,
                    ),
                )
                sequence += 1
            else:
                exhausted += 1
        else:
            served[bucket_index] += 1
            completed += 1
            completion_times.append(event_time)

    last_completion = max(completion_times) if completion_times else None
    drain_after_recovery = (
        max(0.0, last_completion - config.recovery_time)
        if last_completion is not None
        else None
    )
    peak_offered = max(offered, default=0) / config.bucket_width
    peak_recovery_offered = max(offered_after_recovery, default=0) / config.bucket_width

    buckets = tuple(
        BucketRecord(
            index=index,
            start_seconds=index * config.bucket_width,
            end_seconds=min((index + 1) * config.bucket_width, config.end_time),
            offered=offered[index],
            served=served[index],
            rejected_outage=rejected_outage[index],
            rejected_overload=rejected_overload[index],
        )
        for index in range(config.bucket_count)
    )
    summary = SimulationSummary(
        clients=config.clients,
        completed=completed,
        exhausted=exhausted,
        timed_out=timed_out,
        attempts=attempts,
        peak_offered_per_second=peak_offered,
        peak_capacity_ratio=peak_offered / config.capacity_per_second,
        peak_recovery_offered_per_second=peak_recovery_offered,
        peak_recovery_capacity_ratio=(
            peak_recovery_offered / config.capacity_per_second
        ),
        last_completion_seconds=last_completion,
        drain_after_recovery_seconds=drain_after_recovery,
    )

    if completed + exhausted + timed_out != config.clients:
        raise RuntimeError("simulation ended with unaccounted clients")
    return SimulationResult(strategy=strategy, summary=summary, buckets=buckets)


def simulate_many(
    config: SimulationConfig,
    strategies: Iterable[Strategy],
) -> tuple[SimulationResult, ...]:
    """Run several strategies against the same configuration and initial load."""

    selected = tuple(strategies)
    if not selected:
        raise ValueError("at least one strategy is required")
    if len(set(selected)) != len(selected):
        raise ValueError("strategies must not contain duplicates")
    return tuple(simulate(config, strategy) for strategy in selected)
