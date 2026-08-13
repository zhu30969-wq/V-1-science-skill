"""Sampling validation (spec §26): spatial/temporal/spectral grids, Nyquist,
aliasing, FFT consistency and propagation sampling requirements.

A sampling failure blocks scientific conclusions (spec §26) — the
contradiction graph classifies it as SAMPLING_FAILURE, never as a physical
contradiction.
"""

from __future__ import annotations

import numpy as np

from stov_scientist.errors import SamplingError
from stov_scientist.physics.propagation import _alias_free_zmax
from stov_scientist.schemas import SamplingReport, SimulationSpec, ValidationLevel, ValidationResult


def _uniform(axis_values: np.ndarray) -> bool:
    if axis_values.size < 2:
        return False
    spacing = np.diff(axis_values)
    return bool(np.allclose(spacing, spacing[0]))


def validate_sampling(
    spec: SimulationSpec,
    *,
    carrier_frequencies: dict[str, float] | None = None,
    propagation_distance: float | None = None,
    wavelength: float | None = None,
    check_id: str = "sampling-simulation",
) -> tuple[ValidationResult, SamplingReport]:
    """Deterministic sampling checks for a SimulationSpec grid.

    carrier_frequencies: axis -> highest physical frequency (1/base units)
    that must be representable (e.g. optical carrier around omega0 uses the
    *grid pitch*, so this is about envelope bandwidth in practice).

    Propagation sampling requirement (Voelz 2011): for angular-spectrum /
    Fresnel-TF solvers, z <= N dx^2 / lambda per axis.
    """
    grid = spec.grid
    problems: list[str] = []
    warnings: list[str] = []
    details: dict = {}
    nyquist_ok = True
    fft_consistent = True
    propagation_ok: bool | None = None

    # FFT consistency: uniform spacing per axis
    for axis in grid.axes:
        n = grid.shape[tuple(grid.axes).index(axis)]
        sp = grid.spacing.get(axis)
        if sp is None or sp <= 0:
            problems.append(f"axis {axis!r}: missing or non-positive spacing")
            fft_consistent = False
            continue
        extent = grid.domain_extent.get(axis)
        if extent is not None and not np.isclose(n * sp, extent, rtol=1e-6):
            problems.append(
                f"axis {axis!r}: grid extent {extent} != n*spacing = {n * sp}"
            )
            fft_consistent = False
        details[f"spacing_{axis}"] = sp

    # Nyquist for declared spectral content
    carriers = carrier_frequencies or {}
    for axis, f_max in carriers.items():
        if axis not in grid.axes:
            continue
        sp = grid.spacing.get(axis)
        if sp is None or sp <= 0:
            continue
        f_nyq = 1.0 / (2.0 * sp)
        if f_max > f_nyq:
            problems.append(
                f"axis {axis!r}: declared max frequency {f_max:.3g} exceeds "
                f"Nyquist {f_nyq:.3g} (spacing {sp:.3g})"
            )
            nyquist_ok = False
        elif f_max > 0.8 * f_nyq:
            warnings.append(
                f"axis {axis!r}: max frequency {f_max:.3g} within 80% of Nyquist "
                f"{f_nyq:.3g} — little margin"
            )
        details[f"nyquist_{axis}"] = f_nyq

    # Propagation sampling requirement
    if propagation_distance is not None and wavelength is not None:
        propagation_ok = True
        for axis in grid.axes:
            if axis in ("x", "y"):  # transverse axes only
                n = grid.shape[tuple(grid.axes).index(axis)]
                sp = grid.spacing.get(axis)
                if sp is None:
                    continue
                zmax = _alias_free_zmax(n, sp, wavelength)
                details[f"zmax_{axis}"] = zmax
                if propagation_distance > zmax:
                    problems.append(
                        f"axis {axis!r}: z={propagation_distance:.3g} exceeds alias-free "
                        f"bound z_max={zmax:.3g} (Voelz 2011)"
                    )
                    propagation_ok = False

    report = SamplingReport(
        sampling_report_id=f"sampling-{spec.simulation_id}",
        grid_id=grid.grid_id,
        nyquist_ok=nyquist_ok,
        aliasing_risk=problems,
        propagation_sampling_ok=propagation_ok,
        fft_consistency_ok=fft_consistent,
        details=details,
        verdict="PASS" if not problems else "FAIL",
    )
    result = ValidationResult(
        check_id=check_id,
        level=ValidationLevel.SAMPLING,
        name="grid sampling / Nyquist / propagation requirements",
        passed=not problems,
        message="; ".join(problems) if problems else "sampling requirements satisfied",
        warnings=warnings,
        details=details,
    )
    return result, report


def require_uniform_axes(spec: SimulationSpec) -> None:
    """Raise SamplingError when any axis would not allow FFT use."""
    result, _ = validate_sampling(spec)
    if not result.passed:
        raise SamplingError(result.message)
