"""Deterministic retry and jitter simulations."""

from .model import (
    BucketRecord,
    SimulationConfig,
    SimulationResult,
    SimulationSummary,
    Strategy,
    retry_delay,
    simulate,
    simulate_many,
)

__all__ = [
    "BucketRecord",
    "SimulationConfig",
    "SimulationResult",
    "SimulationSummary",
    "Strategy",
    "retry_delay",
    "simulate",
    "simulate_many",
]

__version__ = "0.1.0"
