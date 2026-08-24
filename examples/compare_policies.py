"""Generate a small JSON comparison with the public Python API."""

from retry_jitter_lab import SimulationConfig, Strategy, simulate_many
from retry_jitter_lab.output import render_json

config = SimulationConfig(
    clients=250,
    capacity_per_second=80,
    outage_start=1,
    outage_duration=2,
    seed=42,
)
results = simulate_many(config, (Strategy.NONE, Strategy.FULL))

print(render_json(config, results), end="")
