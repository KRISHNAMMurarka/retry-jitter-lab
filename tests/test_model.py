from __future__ import annotations

import random

import pytest

from retry_jitter_lab import (
    SimulationConfig,
    Strategy,
    retry_delay,
    simulate,
    simulate_many,
)


def test_simulation_is_reproducible_for_the_same_seed() -> None:
    config = SimulationConfig(clients=80, seed=42)

    first = simulate(config, Strategy.FULL)
    second = simulate(config, Strategy.FULL)

    assert first == second


def test_different_seed_changes_stochastic_result() -> None:
    first = simulate(SimulationConfig(clients=80, seed=1), Strategy.FULL)
    second = simulate(SimulationConfig(clients=80, seed=2), Strategy.FULL)

    assert first != second


@pytest.mark.parametrize("strategy", list(Strategy))
def test_every_client_reaches_exactly_one_terminal_state(strategy: Strategy) -> None:
    result = simulate(SimulationConfig(clients=90), strategy)
    summary = result.summary

    assert summary.completed + summary.exhausted + summary.timed_out == 90
    assert summary.attempts >= summary.completed
    assert sum(bucket.offered for bucket in result.buckets) == summary.attempts
    assert all(
        bucket.offered == bucket.served + bucket.rejected for bucket in result.buckets
    )


def test_no_jitter_uses_capped_exponential_delay() -> None:
    rng = random.Random(7)

    delay, state = retry_delay(
        Strategy.NONE,
        retry_index=5,
        rng=rng,
        base_delay=0.5,
        multiplier=2.0,
        max_delay=5.0,
    )

    assert delay == 5.0
    assert state == delay


def test_full_jitter_stays_inside_exponential_window() -> None:
    rng = random.Random(7)

    delay, state = retry_delay(
        Strategy.FULL,
        retry_index=3,
        rng=rng,
        base_delay=0.5,
        multiplier=2.0,
        max_delay=30.0,
    )

    assert 0 <= delay <= 4.0
    assert state == delay


def test_equal_jitter_stays_in_upper_half_of_window() -> None:
    delay, _ = retry_delay(
        Strategy.EQUAL,
        retry_index=3,
        rng=random.Random(7),
        base_delay=0.5,
        multiplier=2.0,
        max_delay=30.0,
    )

    assert 2.0 <= delay <= 4.0


def test_decorrelated_jitter_uses_previous_delay_as_state() -> None:
    delay, state = retry_delay(
        Strategy.DECORRELATED,
        retry_index=4,
        rng=random.Random(7),
        base_delay=0.5,
        multiplier=2.0,
        max_delay=30.0,
        previous_delay=2.0,
    )

    assert 0.5 <= delay <= 6.0
    assert state == delay


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"clients": 0}, "clients"),
        ({"clients": 100_001}, "clients"),
        ({"capacity_per_second": 0}, "capacity_per_second"),
        ({"outage_start": -1}, "outage_start"),
        ({"outage_duration": -1}, "outage_duration"),
        ({"initial_spread": -1}, "initial_spread"),
        ({"base_delay": 0}, "base_delay"),
        ({"multiplier": 0.5}, "multiplier"),
        ({"max_delay": 0.1}, "max_delay"),
        ({"max_retries": 101}, "max_retries"),
        ({"bucket_width": 0}, "bucket_width"),
        ({"end_time": 0.5}, "end_time"),
        ({"end_time": float("inf")}, "finite"),
        (
            {"capacity_per_second": 1, "bucket_width": 0.1},
            "at least one request",
        ),
    ],
)
def test_invalid_configuration_is_rejected(
    changes: dict[str, int | float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        SimulationConfig(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"retry_index": -1},
        {"base_delay": 0},
        {"multiplier": 0.5},
        {"max_delay": 0.1},
    ],
)
def test_invalid_delay_parameters_are_rejected(
    changes: dict[str, int | float],
) -> None:
    parameters: dict[str, object] = {
        "strategy": Strategy.FULL,
        "retry_index": 0,
        "rng": random.Random(2),
        "base_delay": 0.5,
        "multiplier": 2.0,
        "max_delay": 30.0,
    }
    parameters.update(changes)

    with pytest.raises(ValueError):
        retry_delay(**parameters)  # type: ignore[arg-type]


def test_horizon_marks_scheduled_retries_as_timed_out() -> None:
    result = simulate(
        SimulationConfig(
            clients=25,
            capacity_per_second=100,
            outage_duration=10,
            initial_spread=0,
            base_delay=2,
            end_time=2,
        ),
        Strategy.NONE,
    )

    assert result.summary.completed == 0
    assert result.summary.timed_out == 25
    assert result.summary.exhausted == 0


def test_zero_retries_exhausts_requests_rejected_during_outage() -> None:
    result = simulate(
        SimulationConfig(clients=25, max_retries=0, initial_spread=0),
        Strategy.FULL,
    )

    assert result.summary.completed == 0
    assert result.summary.exhausted == 25
    assert result.summary.attempts == 25


def test_simulate_many_preserves_requested_order() -> None:
    results = simulate_many(
        SimulationConfig(clients=20),
        (Strategy.EQUAL, Strategy.NONE),
    )

    assert [result.strategy for result in results] == [Strategy.EQUAL, Strategy.NONE]


def test_jitter_reduces_peak_recovery_load_in_default_scenario() -> None:
    no_jitter, full_jitter = simulate_many(
        SimulationConfig(),
        (Strategy.NONE, Strategy.FULL),
    )

    assert (
        full_jitter.summary.peak_recovery_offered_per_second
        < no_jitter.summary.peak_recovery_offered_per_second
    )


def test_simulate_many_rejects_empty_or_duplicate_selection() -> None:
    config = SimulationConfig(clients=20)

    with pytest.raises(ValueError, match="at least one"):
        simulate_many(config, ())
    with pytest.raises(ValueError, match="duplicates"):
        simulate_many(config, (Strategy.FULL, Strategy.FULL))
