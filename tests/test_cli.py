from __future__ import annotations

import json
from pathlib import Path

import pytest

from retry_jitter_lab.cli import main


def test_cli_prints_selected_strategy_as_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = main(
        [
            "--strategy",
            "equal",
            "--clients",
            "10",
            "--capacity",
            "20",
            "--end-time",
            "8",
            "--format",
            "json",
        ]
    )

    document = json.loads(capsys.readouterr().out)
    assert status == 0
    assert [result["strategy"] for result in document["results"]] == ["equal"]


def test_cli_writes_csv_to_requested_path(tmp_path: Path) -> None:
    output = tmp_path / "report.csv"

    status = main(
        [
            "--strategy",
            "none",
            "--clients",
            "10",
            "--capacity",
            "20",
            "--end-time",
            "8",
            "--format",
            "csv",
            "--output",
            str(output),
        ]
    )

    assert status == 0
    assert output.read_text(encoding="utf-8").startswith("strategy,bucket_index")


def test_cli_rejects_invalid_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--clients", "0"])

    assert raised.value.code == 2
    assert "clients must be" in capsys.readouterr().err
