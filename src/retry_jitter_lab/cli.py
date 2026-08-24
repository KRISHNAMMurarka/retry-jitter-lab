"""Command-line interface for retry-jitter-lab."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .model import SimulationConfig, Strategy, simulate_many
from .output import render_csv, render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""

    parser = argparse.ArgumentParser(
        prog="retry-jitter-lab",
        description=(
            "Compare deterministic retry/backoff strategies in a bucketed "
            "outage and recovery model."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        choices=[strategy.value for strategy in Strategy],
        dest="strategies",
        help=(
            "Strategy to simulate; repeat to choose several. All are used when omitted."
        ),
    )
    parser.add_argument("--clients", type=int, default=600)
    parser.add_argument("--capacity", type=float, default=120.0, metavar="REQ_PER_SEC")
    parser.add_argument("--outage-start", type=float, default=1.0, metavar="SECONDS")
    parser.add_argument("--outage-duration", type=float, default=3.0, metavar="SECONDS")
    parser.add_argument("--initial-spread", type=float, default=0.4, metavar="SECONDS")
    parser.add_argument("--base-delay", type=float, default=0.5, metavar="SECONDS")
    parser.add_argument("--multiplier", type=float, default=2.0)
    parser.add_argument("--max-delay", type=float, default=30.0, metavar="SECONDS")
    parser.add_argument("--max-retries", type=int, default=6)
    parser.add_argument("--bucket-width", type=float, default=0.1, metavar="SECONDS")
    parser.add_argument("--end-time", type=float, default=40.0, metavar="SECONDS")
    parser.add_argument("--seed", type=int, default=20260812)
    parser.add_argument("--format", choices=("text", "json", "csv"), default="text")
    parser.add_argument(
        "--output",
        type=Path,
        metavar="PATH",
        help="Write the report to PATH instead of standard output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit status."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = SimulationConfig(
            clients=args.clients,
            capacity_per_second=args.capacity,
            outage_start=args.outage_start,
            outage_duration=args.outage_duration,
            initial_spread=args.initial_spread,
            base_delay=args.base_delay,
            multiplier=args.multiplier,
            max_delay=args.max_delay,
            max_retries=args.max_retries,
            bucket_width=args.bucket_width,
            end_time=args.end_time,
            seed=args.seed,
        )
    except ValueError as error:
        parser.error(str(error))

    selected = (
        tuple(Strategy(value) for value in args.strategies)
        if args.strategies
        else tuple(Strategy)
    )
    try:
        results = simulate_many(config, selected)
    except ValueError as error:
        parser.error(str(error))

    if args.format == "json":
        report = render_json(config, results)
    elif args.format == "csv":
        report = render_csv(results)
    else:
        report = render_text(config, results)
    if args.output is not None:
        args.output.write_text(report, encoding="utf-8")
    else:
        try:
            sys.stdout.write(report)
        except BrokenPipeError:
            return 0
    return 0
