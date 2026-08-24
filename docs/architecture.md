# Architecture

```text
CLI arguments
    |
    v
validated SimulationConfig
    |
    +--> deterministic initial arrivals
    |
    +--> per-client retry RNGs
    |
    v
priority-queue event loop
    |
    +--> outage rejection
    +--> bucket-capacity rejection
    +--> completion / exhaustion / timeout
    |
    v
SimulationResult
    |
    +--> text summary
    +--> versioned JSON
    +--> bucket-level CSV
```

## Components

- `model.py` owns validation, retry-delay strategies, event ordering, capacity
  accounting, and immutable result types.
- `output.py` converts result types into presentation-independent report
  formats. The JSON schema version is declared here.
- `cli.py` maps user input to configuration, selects strategies, and writes the
  chosen format.

The runtime uses only the Python standard library. Development tools are
optional dependencies.

## Event ordering

Events are ordered by `(time, sequence, client, retry index, previous delay)`.
The monotonic sequence number removes ambiguity when two clients are scheduled
at the same floating-point time.

## Extension boundary

A new retry strategy belongs in the `Strategy` enum and `retry_delay` function.
It must document its state and delay bounds and include deterministic unit
tests. A new report format should consume `SimulationResult` without reaching
back into the event queue.

Changing bucket semantics or terminal-state accounting is a model change and
requires a new model identifier in the JSON envelope.
