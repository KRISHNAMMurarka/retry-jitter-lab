# retry-jitter-lab

[![CI](https://github.com/KRISHNAMMurarka/retry-jitter-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/KRISHNAMMurarka/retry-jitter-lab/actions/workflows/ci.yml)
[![CodeQL](https://github.com/KRISHNAMMurarka/retry-jitter-lab/actions/workflows/codeql.yml/badge.svg)](https://github.com/KRISHNAMMurarka/retry-jitter-lab/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-111827.svg)](./LICENSE)

A deterministic discrete-event simulator for comparing exponential backoff
with no jitter, full jitter, equal jitter, and decorrelated jitter.

It models a cohort of clients retrying through an outage and a capacity-limited
recovery. Use it to inspect load shape and trade-offs, generate reproducible
fixtures, or test retry-policy assumptions before implementing them in a real
client.

> **Maturity: experimental.** Results are simulated, not production
> measurements or performance guarantees.

## What it provides

- four documented retry-delay strategies;
- identical initial load and isolated random streams for fair comparisons;
- reproducible runs from an explicit seed;
- human-readable, versioned JSON, and tabular CSV reports;
- a dependency-free runtime and importable Python API; and
- explicit bucket, capacity, outage, horizon, and retry-limit controls.

## Install

Python 3.10 or newer is required.

```bash
python -m pip install .
```

For development checks:

```bash
python -m pip install -e '.[dev]'
```

The project is not currently published to PyPI. Install from a verified source
checkout.

## Quick start

Compare all strategies with the default deterministic scenario:

```bash
retry-jitter-lab
```

Compare two policies and retain a versioned JSON report:

```bash
retry-jitter-lab \
  --strategy none \
  --strategy full \
  --seed 20260812 \
  --format json \
  --output report.json
```

Export bucket-level data for analysis:

```bash
retry-jitter-lab --format csv > retry-load.csv
```

The default scenario currently produces this summary:

```text
strategy       completed  exhausted  timed out  recovery peak  capacity x  attempts/client  drained after recovery
------------------------------------------------------------------------------------------------------------------
none                 192        408          0         1560.0       13.00            6.520                28.827s
full                 598          2          0          310.0        2.58            5.488                16.161s
equal                600          0          0          510.0        4.25            5.230                11.687s
decorrelated         599          1          0          360.0        3.00            4.213                11.601s
```

These figures are illustrative outputs from this model and seed. Changing the
scenario changes the result.

## Python API

```python
from retry_jitter_lab import SimulationConfig, Strategy, simulate_many

config = SimulationConfig(
    clients=600,
    capacity_per_second=120,
    outage_duration=3,
    seed=20260812,
)

results = simulate_many(config, (Strategy.NONE, Strategy.FULL))
for result in results:
    print(result.strategy.value, result.summary.peak_offered_per_second)
```

[`examples/compare_policies.py`](./examples/compare_policies.py) generates a
complete JSON report with the same public API.

## Strategies

For retry index `n`, `cap = min(max_delay, base_delay * multiplier ** n)`.

| Strategy | Delay |
| --- | --- |
| `none` | `cap` |
| `full` | uniform random value in `[0, cap]` |
| `equal` | `cap / 2 + uniform(0, cap / 2)` |
| `decorrelated` | uniform value between `base_delay` and `min(max_delay, previous_delay * 3)` |

See [Model and assumptions](./docs/model.md) for retry-count semantics,
capacity bucketing, and determinism details.

## Report formats

- **Text** is a compact strategy comparison for humans.
- **JSON** uses a `schema_version` field and includes configuration, summaries,
  and every bucket.
- **CSV** contains one row per strategy and bucket for spreadsheets and data
  tools.

Generated files contain only parameters and simulated results. The tool does
not make network requests or collect telemetry.

## Architecture

The package separates the event model, report serialization, and command-line
adapter. Read [Architecture](./docs/architecture.md) for the data flow and
extension boundary.

## Limitations and non-goals

This is intentionally a small teaching and experimentation model. It does not
model network latency distributions, request deadlines, queue disciplines,
circuit breakers, hedging, adaptive concurrency, server fleets, or correlated
regional failures. It is not a production capacity planner.

The complete boundary is in [Limitations and non-goals](./docs/non-goals.md).

## Development

```bash
ruff format --check .
ruff check .
mypy src
pytest --cov=retry_jitter_lab --cov-branch --cov-report=term-missing
python -m build
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) before proposing a change. Report
suspected vulnerabilities through [SECURITY.md](./SECURITY.md), not a public
issue.

## Provenance

This repository is a clean, brand-neutral extraction of a smaller retry-storm
simulation authored in an Edilec-owned local publishing workspace. The model
was generalized into a package and CLI; no brand assets, rendered media,
production data, credentials, or third-party source code were copied.

See [PROVENANCE.md](./PROVENANCE.md) for the exact extraction boundary.

## Licence

[MIT](./LICENSE) © 2026 Edilec Private Limited. Maintained by
[Krishnam Murarka](https://edilec.com/authors/krishnam-murarka/).
