"""Angular spectrum solvers (spatiotemporal and spatial)."""

from __future__ import annotations

from stov_scientist.physics.fields import OpticalField
from stov_scientist.physics.propagation import (
    AngularSpectrumPropagator,
    PropagationResult,
)
from stov_scientist.simulation.registry import SolverMetadata, SolverRegistry


def _build_xt(spec) -> AngularSpectrumPropagator:
    return AngularSpectrumPropagator()


def _build_xy(spec) -> AngularSpectrumPropagator:
    return AngularSpectrumPropagator(wavelength=float(spec.parameters["wavelength"]))


def _register_angular_spectrum(registry: SolverRegistry) -> None:
    registry.register(
        SolverMetadata(
            solver_id="angular_spectrum_xt",
            name="Angular spectrum (x, t) — vacuum dispersion kz(omega)",
            supported_model_types=("ANALYTICAL", "NUMERICAL"),
            required_inputs=("field_kind", "grid_xt", "propagation_distance"),
            validity_conditions=("linear_only",),
            sampling_requirements=(
                "uniform grid",
                "z <= N dx^2 / lambda per transverse axis (Voelz 2011)",
            ),
            reference_ids=("ref_goodman2017", "ref_voelz2011"),
            version="1.0.0",
            description="Full spatiotemporal transfer function with vacuum "
            "dispersion; evanescent components damped.",
        ),
        _build_xt,
    )
    registry.register(
        SolverMetadata(
            solver_id="angular_spectrum_xy",
            name="Angular spectrum (x, y) — monochromatic",
            supported_model_types=("ANALYTICAL", "NUMERICAL"),
            required_inputs=("field_kind", "grid_xy", "wavelength", "propagation_distance"),
            validity_conditions=("linear_only",),
            sampling_requirements=(
                "uniform grid",
                "z <= N dx^2 / lambda per transverse axis (Voelz 2011)",
            ),
            reference_ids=("ref_goodman2017", "ref_voelz2011"),
            version="1.0.0",
            description="Monochromatic angular spectrum propagation.",
        ),
        _build_xy,
    )


def run_angular_spectrum(
    field: OpticalField, spec, propagator: AngularSpectrumPropagator
) -> PropagationResult:
    z = float(spec.parameters["propagation_distance"])
    if tuple(field.axes) == ("x", "t"):
        carrier = spec.parameters.get("carrier_omega")
        return propagator.propagate_spatiotemporal(
            field, z, carrier_omega=float(carrier) if carrier else None
        )
    return propagator.propagate_spatial(field, z)


def register_angular_spectrum_solvers(registry: SolverRegistry) -> None:
    _register_angular_spectrum(registry)
