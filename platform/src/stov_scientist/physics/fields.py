"""Complex optical field utilities (spec PHASE 6).

Core container: :class:`OpticalField` — a complex field over named axes with
explicit units and convention provenance. Builders cover validated standard
fields (Gaussian beam, spatial OAM vortex) and the STOV linear-vortex ansatz.

Scientific status markers (spec §20):
  VALIDATED        — primary source transcribed, unit/dim checked, limiting
                     cases unit-tested.
  CANDIDATE_MODEL  — plausible form without a completed validation chain;
                     must never feed production conclusions directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from stov_scientist.errors import SchemaError, ValidationError
from stov_scientist.physics.constants import SPEED_OF_LIGHT

Array = NDArray[np.complex128]


@dataclass
class OpticalField:
    """Complex scalar optical field over named axes.

    values[j, i] corresponds to (x[i], t[j]) etc. — first index is the
    SLOWEST axis, matching numpy C-order indexing with axes in order.
    """

    values: Array
    axes: dict[str, NDArray[np.float64]]
    name: str = "field"
    units: dict[str, str] = field(default_factory=dict)
    convention_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    equation_status: str = "VALIDATED"

    def __post_init__(self) -> None:
        values = np.asarray(self.values)
        if not np.iscomplexobj(values):
            values = values.astype(np.complex128)
        self.values = values
        axes_order = tuple(self.axes)
        if len(axes_order) != values.ndim:
            raise SchemaError(
                f"field {self.name!r}: {values.ndim} dims but {len(axes_order)} axes"
            )
        for dim, ax in enumerate(axes_order):
            if self.axes[ax].size != values.shape[dim]:
                raise SchemaError(
                    f"field {self.name!r}: axis {ax!r} has {self.axes[ax].size} "
                    f"points but values.shape[{dim}]={values.shape[dim]}"
                )

    # --- basic observables ------------------------------------------------
    def intensity(self) -> NDArray[np.float64]:
        return np.abs(self.values) ** 2

    def phase(self) -> NDArray[np.float64]:
        return np.angle(self.values)

    def energy(self) -> float:
        """Grid-integrated energy: sum(|E|^2) * product(axis spacings).

        Includes the cell volume so the value is grid-resolution
        independent (a refinement doubling the sample count must not
        change the energy) — this is the convergence-target observable.
        """
        volume = 1.0
        for name in self.axes:
            volume *= self.spacing(name)
        return float(np.sum(self.intensity()) * volume)

    def normalized(self, inplace: bool = False) -> OpticalField:
        norm = np.sqrt(self.energy())
        if norm == 0:
            raise ValidationError(f"field {self.name!r} is identically zero")
        out = self if inplace else self.copy()
        out.values = out.values / norm
        return out

    def copy(self) -> OpticalField:
        return OpticalField(
            values=self.values.copy(),
            axes={k: v.copy() for k, v in self.axes.items()},
            name=self.name,
            units=dict(self.units),
            convention_ids=self.convention_ids,
            source_ids=self.source_ids,
            equation_status=self.equation_status,
        )

    def axis(self, name: str) -> NDArray[np.float64]:
        try:
            return self.axes[name]
        except KeyError as exc:
            raise SchemaError(f"field {self.name!r} has no axis {name!r}") from exc

    def spacing(self, name: str) -> float:
        ax = self.axis(name)
        if ax.size < 2:
            return 0.0
        return float(ax[1] - ax[0])


# ---------------------------------------------------------------------------
# Builders — validated standard fields
# ---------------------------------------------------------------------------


def make_axis(center: float, half_span: float, n: int) -> NDArray[np.float64]:
    if n < 2:
        raise SchemaError(f"axis needs >= 2 points, got {n}")
    if half_span <= 0:
        raise SchemaError(f"half_span must be > 0, got {half_span}")
    return np.linspace(center - half_span, center + half_span, n)


def gaussian_envelope(
    axes: dict[str, NDArray[np.float64]],
    widths: dict[str, float],
    name: str = "gaussian_envelope",
) -> OpticalField:
    """E = exp( -sum_a a^2 / w_a^2 ) over named axes.

    Validated: Gaussian beam envelope (Goodman 2017 §3.3), dimensionless.
    Limiting case: widths -> inf gives a constant field (unit-tested).
    """
    for ax in axes:
        if ax not in widths:
            raise SchemaError(f"missing width for axis {ax!r}")
    mesh = np.meshgrid(*(axes[a] for a in axes), indexing="ij", sparse=False)
    exponent = np.zeros(mesh[0].shape, dtype=np.float64)
    for a, mg in zip(axes, mesh, strict=True):
        w = widths[a]
        if w <= 0:
            raise SchemaError(f"width for axis {a!r} must be > 0, got {w}")
        exponent = exponent + (mg / w) ** 2
    values = np.exp(-exponent).astype(np.complex128)
    return OpticalField(
        values=values,
        axes=dict(axes),
        name=name,
        convention_ids=("units_si", "norm_unity_l2"),
        source_ids=("ref_goodman2017",),
        equation_status="VALIDATED",
    )


def spatial_vortex(
    x: NDArray[np.float64],
    y: NDArray[np.float64],
    wx: float,
    wy: float,
    charge: int = 1,
    name: str = "spatial_oam_vortex",
) -> OpticalField:
    """E(x,y) = (x + i sgn(l) y)^|l| exp(-(x^2/wx^2 + y^2/wy^2)).

    Validated standard spatial OAM vortex (charge sign per
    ``phase_sign_oam_xy``). Limiting case charge=0 -> Gaussian.
    """
    if abs(charge) < 1:
        base = gaussian_envelope({"x": x, "y": y}, {"x": wx, "y": wy})
        base.name = name
        return base
    xx, yy = np.meshgrid(x, y, indexing="ij")
    sgn = 1.0 if charge > 0 else -1.0
    vortex = (xx + 1j * sgn * yy) ** abs(charge)
    env = np.exp(-((xx / wx) ** 2 + (yy / wy) ** 2))
    return OpticalField(
        values=vortex * env,
        axes={"x": x, "y": y},
        name=name,
        convention_ids=("coord_xy_z_prop", "phase_sign_oam_xy", "units_si"),
        source_ids=("ref_goodman2017",),
        equation_status="VALIDATED",
    )


def stov_vortex(
    x: NDArray[np.float64],
    t: NDArray[np.float64],
    wx: float,
    wt: float,
    charge: int = 1,
    name: str = "stov_vortex",
) -> OpticalField:
    """E(x,t) = (x + i sgn(l) c0 t)^|l| exp(-(x^2/wx^2 + t^2/wt^2)).

    Linear spatiotemporal vortex ansatz (Chong et al. 2020 form): the
    spatiotemporal coordinate is x + i·c0·t (c0 = speed of light), so the
    vortex factor is dimensionally consistent and the charge +1 phase is
    phi = atan2(c0 t, x) per ``phase_sign_stov_xt``. Using c0·t (rather
    than bare t) keeps the phase structure resolved on SI grids — with
    bare seconds the vortex core is sub-resolution for realistic
    ps-scale pulses (see skills/stov-optical-sampling).

    VALIDATED: transcription from primary source; unit/dim checks and
    limiting cases (t=0 -> real x^|l| envelope; x=0 -> (i sgn(l) c0 t)^|l|
    envelope; charge 0 -> Gaussian) are unit-tested.
    """
    if abs(charge) < 1:
        base = gaussian_envelope({"x": x, "t": t}, {"x": wx, "t": wt})
        base.name = name
        base.convention_ids = ("coord_xyt_z_prop", "units_si")
        return base
    xx, tt = np.meshgrid(x, t, indexing="ij")
    sgn = 1.0 if charge > 0 else -1.0
    c0 = SPEED_OF_LIGHT
    vortex = (xx + 1j * sgn * c0 * tt) ** abs(charge)
    env = np.exp(-((xx / wx) ** 2 + (tt / wt) ** 2))
    return OpticalField(
        values=vortex * env,
        axes={"x": x, "t": t},
        name=name,
        convention_ids=("coord_xyt_z_prop", "phase_sign_stov_xt", "units_si"),
        source_ids=("ref_chong2020",),
        equation_status="VALIDATED",
    )


def plane_wave_xt(
    x: NDArray[np.float64],
    t: NDArray[np.float64],
    kx: float = 0.0,
    omega0: float = 0.0,
    name: str = "plane_wave_xt",
) -> OpticalField:
    """E(x,t) = exp(i kx x - i omega0 t) (harmonic exp(-i omega t)).

    Validated plane wave; limiting case kx=omega0=0 -> constant unit field.
    """
    xx, tt = np.meshgrid(x, t, indexing="ij")
    values = np.exp(1j * kx * xx - 1j * omega0 * tt).astype(np.complex128)
    return OpticalField(
        values=values,
        axes={"x": x, "t": t},
        name=name,
        convention_ids=("coord_xyt_z_prop", "harmonic_exp_neg_iwt", "units_si"),
        source_ids=("ref_goodman2017",),
        equation_status="VALIDATED",
    )


def gaussian_beam_parameters(wavelength: float, w0: float) -> dict[str, Any]:
    """Rayleigh range and waist relations for a Gaussian beam (Goodman §3.3).

    zR = pi w0^2 / lambda.  Validated standard relation.
    """
    if w0 <= 0 or wavelength <= 0:
        raise SchemaError("w0 and wavelength must be positive")
    zr = float(np.pi * w0**2 / wavelength)
    return {
        "z_rayleigh": zr,
        "beam_divergence_half_angle": float(wavelength / (np.pi * w0)),
        "confocal_parameter": 2 * zr,
    }
