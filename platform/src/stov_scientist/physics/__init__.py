"""Deterministic physics + numerical core (spec PHASE 6)."""

from stov_scientist.physics.fields import OpticalField
from stov_scientist.physics.propagation import (
    SPEED_OF_LIGHT,
    AngularSpectrumPropagator,
    FresnelPropagator,
    SplitStepConfig,
    SplitStepPropagator,
)

__all__ = [
    "SPEED_OF_LIGHT",
    "AngularSpectrumPropagator",
    "FresnelPropagator",
    "OpticalField",
    "SplitStepConfig",
    "SplitStepPropagator",
]
