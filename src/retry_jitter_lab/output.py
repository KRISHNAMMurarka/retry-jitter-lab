"""Text, JSON, and CSV report rendering."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable
from typing import Any

from .model import SimulationConfig, SimulationResult

SCHEMA_VERSION = "1.0"


def report_document(
    config: SimulationConfig,
    results: Iterable[SimulationResult],
) -> dict[str, Any]:
    """Build the stable JSON report envelope."""

    return {
        "schema_version": SCHEMA_VERSION,
        "model": "bucketed-retry-outage-v1",
        "configuration": config.to_dict(),
        "results": [result.to_dict() for result in results],
    }


def render_json(
    config: SimulationConfig,
    results: Iterable[SimulationResult],
) -> str:
    """Render an indented JSON report."""

    return json.dumps(report_document(config, results), indent=2, sort_keys=True) + "\n"


def render_csv(results: Iterable[SimulationResult]) -> str:
    """Render one row per strategy and time bucket."""

    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        [
            "strategy",
            "bucket_index",
            "start_seconds",
            "end_seconds",
            "offered",
            "served",
            "rejected",
            "rejected_outage",
            "rejected_overload",
        ]
    )
    for result in results:
        for bucket in result.buckets:
            writer.writerow(
                [
                    result.strategy.value,
                    bucket.index,
                    _decimal(bucket.start_seconds),
                    _decimal(bucket.end_seconds),
                    bucket.offered,
                    bucket.served,
                    bucket.rejected,
                    bucket.rejected_outage,
                    bucket.rejected_overload,
                ]
            )
    return stream.getvalue()


def render_text(
    config: SimulationConfig,
    results: Iterable[SimulationResult],
) -> str:
    """Render a compact human-readable comparison."""

    lines = [
        "Retry jitter lab",
        (
            f"{config.clients} clients | {config.capacity_per_second:g} req/s "
            f"capacity | outage {config.outage_start:g}s-"
            f"{config.recovery_time:g}s | seed {config.seed}"
        ),
        "",
        (
            "strategy       completed  exhausted  timed out  recovery peak  "
            "capacity x  attempts/client  drained after recovery"
        ),
        "-" * 111,
    ]
    for result in results:
        summary = result.summary
        drained = (
            f"{summary.drain_after_recovery_seconds:.3f}s"
            if summary.drain_after_recovery_seconds is not None
            else "n/a"
        )
        lines.append(
            f"{result.strategy.value:<14} "
            f"{summary.completed:>9}  "
            f"{summary.exhausted:>9}  "
            f"{summary.timed_out:>9}  "
            f"{summary.peak_recovery_offered_per_second:>13.1f}  "
            f"{summary.peak_recovery_capacity_ratio:>10.2f}  "
            f"{summary.attempts_per_client:>15.3f}  "
            f"{drained:>22}"
        )
    lines.extend(
        [
            "",
            "Simulated model, not a production measurement or performance guarantee.",
        ]
    )
    return "\n".join(lines) + "\n"


def _decimal(value: float) -> str:
    """Format decimal seconds without binary-float noise."""

    return f"{value:.12g}"
