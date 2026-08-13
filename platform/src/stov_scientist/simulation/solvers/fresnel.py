"""Fresnel (paraxial) solver — monochromatic spatial propagation."""

from __future__ import annotations

from stov_scientist.physics.fields import OpticalField
from stov_scientist.physics.propagation import FresnelPropagator, PropagationResult
from stov_scientist.simulation.registry import SolverMetadata, SolverRegistry


def _build(spec) -> FresnelPropagator:
    return FresnelPropagator(wavelength=float(spec.parameters["wavelength"]))


def register_fresnel_solvers(registry: SolverRegistry) -> None:
    registry.register(
        SolverMetadata(
            solver_id="fresnel_xy",
            name="Fresnel paraxial propagation (x, y)",
            supported_model_types=("ANALYTICAL",),
            required_inputs=("field_kind", "grid_xy", "wavelength", "propagation_distance"),
            validity_conditions=("linear_only", "paraxial_only"),
            sampling_requirements=(
                "uniform grid",
                "z <= N dx^2 / lambda per transverse axis (Voelz 2011)",
                "paraxial regime: Fresnel number considerations",
            ),
            reference_ids=("ref_goodman2017", "ref_voelz2011"),
            version="1.0.0",
            description="Paraxial Fresnel transfer-function propagation.",
        ),
        _build,
    )


def run_fresnel(field: OpticalField, spec, propagator: FresnelPropagator) -> PropagationResult:
    z = float(spec.parameters["propagation_distance"])
    return propagator.propagate_spatial(field, z)
