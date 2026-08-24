from __future__ import annotations

import csv
import io
import json

from retry_jitter_lab import (
    SimulationConfig,
    SimulationResult,
    Strategy,
    simulate_many,
)
from retry_jitter_lab.output import render_csv, render_json, render_text


def sample() -> tuple[SimulationConfig, tuple[SimulationResult, ...]]:
    config = SimulationConfig(
        clients=12,
        capacity_per_second=20,
        bucket_width=0.1,
        end_time=8,
    )
    return config, simulate_many(config, (Strategy.NONE, Strategy.FULL))


def test_json_report_has_versioned_envelope_and_all_buckets() -> None:
    config, results = sample()

    document = json.loads(render_json(config, results))

    assert document["schema_version"] == "1.0"
    assert document["model"] == "bucketed-retry-outage-v1"
    assert document["configuration"]["clients"] == 12
    assert [result["strategy"] for result in document["results"]] == [
        "none",
        "full",
    ]
    assert len(document["results"][0]["buckets"]) == config.bucket_count


def test_csv_report_has_one_row_per_strategy_and_bucket() -> None:
    config, results = sample()

    rows = list(csv.DictReader(io.StringIO(render_csv(results))))

    assert len(rows) == config.bucket_count * 2
    assert rows[0]["strategy"] == "none"
    assert rows[-1]["strategy"] == "full"
    assert int(rows[0]["offered"]) == (
        int(rows[0]["served"]) + int(rows[0]["rejected"])
    )


def test_text_report_labels_model_as_simulated() -> None:
    config, results = sample()

    report = render_text(config, results)

    assert "Retry jitter lab" in report
    assert "none" in report
    assert "full" in report
    assert "Simulated model" in report
