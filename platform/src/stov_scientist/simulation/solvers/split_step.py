"""Split-step solver (generic framework; linear step = angular spectrum)."""

from __future__ import annotations

from stov_scientist.physics.fields import OpticalField
from stov_scientist.physics.propagation import (
    AngularSpectrumPropagator,
    PropagationResult,
    SplitStepConfig,
    SplitStepPropagator,
)
from stov_scientist.simulation.registry import SolverMetadata, SolverRegistry


def _build(spec) -> SplitStepPropagator:
    n_steps = int(spec.parameters.get("n_steps", 10))
    return SplitStepPropagator(
        SplitStepConfig(linear_propagator=AngularSpectrumPropagator(), n_steps=n_steps)
    )


def register_split_step_solvers(registry: SolverRegistry) -> None:
    registry.register(
        SolverMetadata(
            solver_id="split_step_xt",
            name="Split-step propagation (x, t) with angular-spectrum linear step",
            supported_model_types=("ANALYTICAL", "NUMERICAL"),
            required_inputs=("field_kind", "grid_xt", "propagation_distance"),
            validity_conditions=("linear_only",),
            sampling_requirements=(
                "uniform grid",
                "z <= N dx^2 / lambda per transverse axis (Voelz 2011)",
            ),
            reference_ids=("ref_schmidt2010", "ref_goodman2017"),
            version="1.0.0",
            description="Split-step framework; with nonlinear_coefficient=0 it "
            "must match single-shot angular spectrum (unit-tested).",
        ),
        _build,
    )


def run_split_step(field: OpticalField, spec, propagator: SplitStepPropagator) -> PropagationResult:
    z = float(spec.parameters["propagation_distance"])
    carrier = spec.parameters.get("carrier_omega")
    return propagator.propagate(
        field, z, linear_kwargs={"carrier_omega": float(carrier) if carrier else None}
    )
