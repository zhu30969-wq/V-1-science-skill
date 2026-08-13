"""Deterministic initial-field builders (SimulationSpec -> OpticalField).

Each builder declares its parameter contract; the runner validates that the
SimulationSpec parameters satisfy it BEFORE building. No builder accepts
unknown parameters silently.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from stov_scientist.errors import SchemaError
from stov_scientist.physics.fields import (
    OpticalField,
    gaussian_envelope,
    make_axis,
    plane_wave_xt,
    spatial_vortex,
    stov_vortex,
)


@dataclass(frozen=True)
class FieldBuilder:
    kind: str
    axes: tuple[str, ...]
    required_params: tuple[str, ...]
    optional_params: tuple[str, ...] = ()
    description: str = ""
    source_ids: tuple[str, ...] = ()


def _check_params(kind: str, params: dict[str, float | str], required: tuple[str, ...], optional: tuple[str, ...]) -> None:
    missing = [p for p in required if p not in params]
    if missing:
        raise SchemaError(f"field_kind={kind!r} missing parameters: {missing}")
    allowed = set(required) | set(optional) | {
        "wavelength",
        "propagation_distance",
        "carrier_omega",
        "nonlinear_coefficient",
        "field_kind",
        "random_seed",
        "turbulence_model",
        "cn2",
        "l0",
        "L0",
        "n_steps",
        "nx",
        "nt",
    }
    unknown = [p for p in params if p not in allowed]
    if unknown:
        raise SchemaError(f"field_kind={kind!r} unknown parameters: {unknown}")


def _axes_from_spec(spec_axes: tuple[str, ...], spacing: dict[str, float], extent: dict[str, float], shape: tuple[int, ...]) -> dict[str, NDArray[np.float64]]:
    axes: dict[str, NDArray[np.float64]] = {}
    for name, n, sp, ext in zip(spec_axes, shape, [spacing[a] for a in spec_axes], [extent[a] for a in spec_axes], strict=True):
        axes[name] = make_axis(0.0, ext / 2, n)
        # rebuild with exact spacing (make_axis uses n points, spacing = ext/(n-1))
        axes[name] = np.linspace(-ext / 2, ext / 2 - 0 * sp, n).astype(np.float64)
        # ensure exact spacing consistency with declared spacing
        axes[name] = (np.arange(n) * sp - (n - 1) * sp / 2).astype(np.float64)
    return axes


def build_initial_field(field_kind: str, spec_axes: tuple[str, ...], spec_shape: tuple[int, ...], spacing: dict[str, float], extent: dict[str, float], params: dict[str, float | str]) -> OpticalField:
    """Dispatch to the built-in deterministic builders."""
    axes = _axes_from_spec(spec_axes, spacing, extent, spec_shape)
    if field_kind == "stov_vortex_xt":
        _check_params(field_kind, params, ("wx", "wt"), ("charge",))
        charge = int(params.get("charge", 1))
        return stov_vortex(axes["x"], axes["t"], float(params["wx"]), float(params["wt"]), charge=charge)
    if field_kind == "gaussian_xt":
        _check_params(field_kind, params, ("wx", "wt"), ())
        return gaussian_envelope({"x": axes["x"], "t": axes["t"]}, {"x": float(params["wx"]), "t": float(params["wt"])})
    if field_kind == "spatial_vortex_xy":
        _check_params(field_kind, params, ("wx", "wy"), ("charge",))
        charge = int(params.get("charge", 1))
        return spatial_vortex(axes["x"], axes["y"], float(params["wx"]), float(params["wy"]), charge=charge)
    if field_kind == "gaussian_xy":
        _check_params(field_kind, params, ("wx", "wy"), ())
        return gaussian_envelope({"x": axes["x"], "y": axes["y"]}, {"x": float(params["wx"]), "y": float(params["wy"])})
    if field_kind == "plane_wave_xt":
        _check_params(field_kind, params, (), ("kx", "omega0"))
        return plane_wave_xt(axes["x"], axes["t"], float(params.get("kx", 0.0)), float(params.get("omega0", 0.0)))
    if field_kind == "stov_vortex_turbulent_xt":
        # turbulent initial phase applied to the STOV vortex (Phase 7 §31)
        from stov_scientist.physics.turbulence import PhaseScreenGenerator

        _check_params(field_kind, params, ("wx", "wt", "cn2", "l0", "L0"), ("charge", "turbulence_model", "random_seed"))
        charge = int(params.get("charge", 1))
        field = stov_vortex(axes["x"], axes["t"], float(params["wx"]), float(params["wt"]), charge=charge)
        generator = PhaseScreenGenerator(
            str(params.get("turbulence_model", "kolmogorov_vk")),
            seed=int(params.get("random_seed", 0)),
        )
        screen = generator.generate_phase_screen(
            (len(axes["x"]), len(axes["t"])),
            spacing["x"],
            {"cn2": float(params["cn2"]), "l0": float(params["l0"]), "L0": float(params["L0"])},
        )
        field.values = field.values * np.exp(1j * screen.T)
        field.name = "stov_vortex_turbulent"
        return field
    raise SchemaError(f"unknown field_kind {field_kind!r}")
