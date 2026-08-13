"""Free-space propagation (spec PHASE 6).

  * Angular spectrum propagator — full (non-paraxial) transfer function,
    spatial (x, y) and spatiotemporal (x, t) variants.
  * Fresnel (paraxial) propagator — transfer-function form.
  * Generic split-step framework (linear step + optional nonlinear phase).

Validated methods (Goodman 2017 §3.10/§4.1; Voelz 2011 ch. 6-7). The vacuum
dispersion relation k_z(omega) = sqrt((omega/c)^2 - kx^2) makes the temporal
envelope translate rigidly in vacuum (no GVD) — unit-tested limiting case.

Alias-free sampling bound (Voelz 2011): with N samples at pitch dx, the
angular-spectrum transfer function is alias-free for z <= N dx^2 / lambda.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from stov_scientist.errors import SamplingError, SchemaError, SolverError
from stov_scientist.physics.constants import SPEED_OF_LIGHT
from stov_scientist.physics.fields import OpticalField


def _alias_free_zmax(n: int, dx: float, wavelength: float) -> float:
    """Voelz 2011: z_max = N dx^2 / lambda for the angular spectrum TF form."""
    return float(n * dx**2 / wavelength)


def _k_components(
    shape: tuple[int, ...], spacing: tuple[float, ...]
) -> tuple[NDArray[np.float64], ...]:
    """Angular frequencies for each axis (rad per base unit), C-order."""
    return tuple(
        2 * np.pi * np.fft.fftfreq(n, d=sp) for n, sp in zip(shape, spacing, strict=True)
    )


@dataclass
class PropagationResult:
    field: OpticalField
    distance: float
    method: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Angular spectrum
# ---------------------------------------------------------------------------


class AngularSpectrumPropagator:
    """Full (non-paraxial) angular spectrum propagation (Goodman §3.10).

    Spatial variant: E(x,y,z) with k_z = sqrt(k^2 - kx^2 - ky^2).
    Spatiotemporal variant: E(x,t,z) with k_z(omega) = sqrt((omega/c)^2 - kx^2).
    """

    method = "angular_spectrum"

    def __init__(self, wavelength: float | None = None):
        if wavelength is not None and wavelength <= 0:
            raise SchemaError(f"wavelength must be > 0, got {wavelength}")
        self.wavelength = wavelength

    # -- spatial (x, y) ----------------------------------------------------
    def propagate_spatial(
        self, field: OpticalField, z: float, wavelength: float | None = None
    ) -> PropagationResult:
        lam = wavelength if wavelength is not None else self.wavelength
        if lam is None or lam <= 0:
            raise SchemaError("wavelength required for spatial propagation")
        if z < 0:
            raise SolverError(f"z must be >= 0 for forward propagation, got {z}")
        if set(field.axes) != {"x", "y"}:
            raise SchemaError("spatial propagation requires axes (x, y)")

        dx, dy = field.spacing("x"), field.spacing("y")
        if dx <= 0 or dy <= 0:
            raise SamplingError("spatial grid spacing must be positive")

        k = 2 * np.pi / lam
        kx, ky = _k_components(field.values.shape, (dx, dy))
        kx_m, ky_m = np.meshgrid(kx, ky, indexing="ij")
        kz_sq = k**2 - kx_m**2 - ky_m**2
        if np.any(kz_sq < 0):
            # evanescent components: keep them damped, never amplified
            kz = np.where(kz_sq >= 0, np.sqrt(np.clip(kz_sq, 0, None)), 0.0j)
            kz = np.where(kz_sq < 0, 1j * np.sqrt(-np.where(kz_sq < 0, kz_sq, 0.0)), kz)
            evanescent = True
        else:
            kz = np.sqrt(kz_sq)
            evanescent = False

        warnings = []
        zmax = _alias_free_zmax(field.values.shape[0], dx, lam)
        zmax = min(zmax, _alias_free_zmax(field.values.shape[1], dy, lam))
        if z > zmax:
            warnings.append(
                f"z={z:.3g} exceeds alias-free bound z_max={zmax:.3g} "
                "(Voelz 2011); wrap-around aliasing possible"
            )
        if evanescent:
            warnings.append("evanescent components present; damped, not amplified")

        transfer = np.exp(1j * kz * z)
        spectrum = np.fft.fftn(field.values)
        out = np.fft.ifftn(spectrum * transfer)
        result = field.copy()
        result.values = out
        result.name = f"{field.name}@z={z:.3g}"
        return PropagationResult(result, z, self.method, warnings)

    # -- spatiotemporal (x, t) ----------------------------------------------
    def propagate_spatiotemporal(
        self,
        field: OpticalField,
        z: float,
        carrier_omega: float | None = None,
    ) -> PropagationResult:
        """E(x,t,z) with vacuum dispersion k_z(omega) = sqrt((w/c)^2 - kx^2).

        ``carrier_omega``: the optical carrier frequency omega0 (rad/s) of the
        ENVELOPE representation. The field axis carries the envelope time
        offset; the dispersion is evaluated at omega0 + delta_omega. Without
        the carrier the envelope is baseband and every non-zero spatial
        frequency is evanescent — a near-field, not a propagating pulse.

        In vacuum d^2 k_z / d omega^2 = 0 on axis; for the on-axis plane-wave
        limit the envelope translates rigidly (no vacuum GVD) — unit-tested.
        """
        if z < 0:
            raise SolverError(f"z must be >= 0 for forward propagation, got {z}")
        if set(field.axes) != {"x", "t"}:
            raise SchemaError("spatiotemporal propagation requires axes (x, t)")

        dx, dt = field.spacing("x"), field.spacing("t")
        if dx <= 0 or dt <= 0:
            raise SamplingError("spatiotemporal grid spacing must be positive")

        kx, om = _k_components(field.values.shape, (dx, dt))
        # kx in rad/m; om = angular frequency offset in rad/s (axis is centered)
        kx_m, om_m = np.meshgrid(kx, om, indexing="ij")
        carrier = 0.0 if carrier_omega is None else carrier_omega
        kz_sq = ((om_m + carrier) / SPEED_OF_LIGHT) ** 2 - kx_m**2
        kz = np.zeros_like(kz_sq, dtype=np.complex128)
        mask_ev = kz_sq < 0
        kz[~mask_ev] = np.sqrt(kz_sq[~mask_ev])
        kz[mask_ev] = 1j * np.sqrt(-kz_sq[mask_ev])

        warnings: list[str] = []
        if carrier == 0.0 and mask_ev.any():
            warnings.append(
                "evanescent spatiotemporal components; damped — no carrier "
                "frequency given, envelope propagated as baseband (near-field)"
            )
        elif mask_ev.any():
            warnings.append("evanescent spatiotemporal components; damped")

        transfer = np.exp(1j * kz * z)
        spectrum = np.fft.fftn(field.values)
        out = np.fft.ifftn(spectrum * transfer)
        result = field.copy()
        result.values = out
        result.name = f"{field.name}@z={z:.3g}"
        return PropagationResult(result, z, self.method, warnings)


# ---------------------------------------------------------------------------
# Fresnel (paraxial)
# ---------------------------------------------------------------------------


class FresnelPropagator:
    """Paraxial Fresnel propagation, transfer-function form (Goodman §4.1).

    H(fx, fy) = exp(i k z) exp(-i pi lambda z (fx^2 + fy^2)).
    """

    method = "fresnel"

    def __init__(self, wavelength: float):
        if wavelength <= 0:
            raise SchemaError(f"wavelength must be > 0, got {wavelength}")
        self.wavelength = wavelength

    def propagate_spatial(self, field: OpticalField, z: float) -> PropagationResult:
        if z < 0:
            raise SolverError(f"z must be >= 0, got {z}")
        if set(field.axes) != {"x", "y"}:
            raise SchemaError("Fresnel propagation requires axes (x, y)")
        lam = self.wavelength
        dx, dy = field.spacing("x"), field.spacing("y")
        k = 2 * np.pi / lam
        kx, ky = _k_components(field.values.shape, (dx, dy))
        kx_m, ky_m = np.meshgrid(kx, ky, indexing="ij")
        transfer = np.exp(1j * k * z) * np.exp(-1j * np.pi * lam * z * (kx_m**2 + ky_m**2))

        warnings = []
        zmax = _alias_free_zmax(field.values.shape[0], dx, lam)
        zmax = min(zmax, _alias_free_zmax(field.values.shape[1], dy, lam))
        if z > zmax:
            warnings.append(
                f"z={z:.3g} exceeds alias-free bound z_max={zmax:.3g} (Voelz 2011)"
            )

        out = np.fft.ifftn(np.fft.fftn(field.values) * transfer)
        result = field.copy()
        result.values = out
        result.name = f"{field.name}@z={z:.3g}"
        return PropagationResult(result, z, self.method, warnings)


# ---------------------------------------------------------------------------
# Split-step framework
# ---------------------------------------------------------------------------


@dataclass
class SplitStepConfig:
    linear_propagator: object
    nonlinear_phase: object | None = None
    n_steps: int = 10

    def __post_init__(self) -> None:
        if self.n_steps < 1:
            raise SchemaError("n_steps must be >= 1")


class SplitStepPropagator:
    """Generic split-step framework (Schmidt 2010 ch. 6).

    Linear propagation via a sub-propagator per step; optional nonlinear
    phase accumulation slot. With ``nonlinear_phase=None`` the result must
    match single-shot linear propagation (unit-tested consistency check).

    NOTE: any concrete nonlinear model passed here must itself carry a
    VALIDATED source chain; the framework does not validate model physics.
    """

    method = "split_step"

    def __init__(self, config: SplitStepConfig):
        self.config = config

    def propagate(
        self,
        field: OpticalField,
        z: float,
        *,
        linear_kwargs: dict | None = None,
    ) -> PropagationResult:
        kwargs = linear_kwargs or {}
        dz = z / self.config.n_steps
        current = field
        for _ in range(self.config.n_steps):
            res = _call_propagator(self.config.linear_propagator, current, dz, **kwargs)
            current = res.field
            if self.config.nonlinear_phase is not None:
                phase = _call_nonlinear(self.config.nonlinear_phase, current, dz)
                current = current.copy()
                current.values = current.values * np.exp(1j * phase)
        return PropagationResult(current, z, self.method, [])


def _call_propagator(propagator: object, field: OpticalField, z: float, **kw: object) -> PropagationResult:
    """Dispatch to spatial/spatiotemporal method by the field's axes."""
    if hasattr(propagator, "propagate_spatiotemporal") and set(field.axes) == {"x", "t"}:
        return cast(Any, propagator).propagate_spatiotemporal(field, z, **kw)
    if hasattr(propagator, "propagate_spatial"):
        return cast(Any, propagator).propagate_spatial(field, z, **kw)
    raise SolverError(f"propagator {type(propagator).__name__} has no supported method")


def _call_nonlinear(nonlinear_phase: object, field: OpticalField, dz: float) -> NDArray[np.float64]:
    callable_ = getattr(nonlinear_phase, "phase_accumulation", None)
    if callable_ is None:
        raise SolverError(
            f"nonlinear object {type(nonlinear_phase).__name__} lacks phase_accumulation()"
        )
    return np.asarray(callable_(field, dz), dtype=np.float64)
