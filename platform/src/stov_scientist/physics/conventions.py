"""Convention Registry (spec §21, PHASE 6).

Every ScientificModelSpec must declare ``convention_ids``. Equations from
different papers are never mixed without first aligning conventions.

Reference record for each convention:
  ref_goodman2017 : J. W. Goodman, "Introduction to Fourier Optics",
                    4th ed., W. H. Freeman (2017)
  ref_voelz2011   : D. G. Voelz, "Computational Fourier Optics: A MATLAB
                    Tutorial", SPIE Press (2011)
  ref_chong2020   : A. Chong, C. Wan, J. Chen, Q. Zhan, "Generation of
                    spatiotemporal optical vortices with controllable
                    transverse orbital angular momentum", Nature Photonics
                    14, 350-354 (2020)
  ref_bliokh2012  : K. Y. Bliokh, F. Nori, "Spatiotemporal vortex beams and
                    angular momentum", Phys. Rev. A 86, 033824 (2012)
"""

from __future__ import annotations

from dataclasses import dataclass

from stov_scientist.errors import SchemaError

# ---------------------------------------------------------------------------
# Convention categories
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Convention:
    convention_id: str
    category: str
    name: str
    definition: str
    source_ids: tuple[str, ...]


CONVENTION_REGISTRY: dict[str, Convention] = {
    # --- coordinate / propagation --------------------------------------
    "coord_xyt_z_prop": Convention(
        "coord_xyt_z_prop",
        "coordinate",
        "STOV transverse plane (x, t), propagation along +z",
        "Right-handed (x, t) transverse spatiotemporal plane; z is the "
        "propagation axis; y is the transverse-OAM axis for the (x,t) vortex.",
        ("ref_chong2020",),
    ),
    "coord_xy_z_prop": Convention(
        "coord_xy_z_prop",
        "coordinate",
        "Spatial transverse plane (x, y), propagation along +z",
        "Right-handed (x, y) transverse plane; z propagation axis. Standard "
        "spatial optics convention.",
        ("ref_goodman2017",),
    ),
    # --- Fourier transform ----------------------------------------------
    "ft_space_exp_neg": Convention(
        "ft_space_exp_neg",
        "fourier_transform",
        "Spatial FT: forward exp(-i 2pi f_x x)",
        "Forward transform U(f_x) = integral u(x) exp(-i 2 pi f_x x) dx; "
        "inverse u(x) = integral U(f_x) exp(+i 2 pi f_x x) df_x. "
        "Matches numpy.fft.fftn as forward (Goodman eq. 3-1 sign).",
        ("ref_goodman2017", "ref_voelz2011"),
    ),
    "ft_time_exp_pos": Convention(
        "ft_time_exp_pos",
        "fourier_transform",
        "Temporal FT: u(t) = (1/2pi) integral U(omega) exp(-i omega t) domega",
        "Forward temporal transform U(omega) = integral u(t) exp(+i omega t) dt "
        "(numpy.fft.ifftn kernel); inverse carries exp(-i omega t). "
        "Harmonic time dependence is exp(-i omega t).",
        ("ref_goodman2017",),
    ),
    # --- temporal frequency ---------------------------------------------
    "harmonic_exp_neg_iwt": Convention(
        "harmonic_exp_neg_iwt",
        "temporal_frequency",
        "Time-harmonic fields: exp(-i omega t)",
        "All monochromatic/phased fields use exp(-i omega t). Positive "
        "frequency omega > 0 corresponds to standard optical angular frequency.",
        ("ref_goodman2017",),
    ),
    # --- phase sign ------------------------------------------------------
    "phase_sign_stov_xt": Convention(
        "phase_sign_stov_xt",
        "phase_sign",
        "STOV vortex phase phi = atan2(c0*t, x) for charge +1",
        "Charge +1 STOV ansatz: E(x,t) ~ (x + i c0 t) G(x,t), phase "
        "atan2(c0 t, x) with c0 the speed of light (spatiotemporal "
        "coordinate x + i c0 t), counterclockwise winding in the "
        "(x, c0 t) plane (Chong et al. 2020 form).",
        ("ref_chong2020",),
    ),
    "phase_sign_oam_xy": Convention(
        "phase_sign_oam_xy",
        "phase_sign",
        "Spatial vortex phase phi = atan2(y, x) for charge +1",
        "Charge +1 spatial vortex: E(x,y) ~ (x + i y) G(x,y).",
        ("ref_goodman2017",),
    ),
    # --- normalization ---------------------------------------------------
    "norm_unity_l2": Convention(
        "norm_unity_l2",
        "normalization",
        "Unit L2 norm option",
        "Fields may be normalized so that sum |E|^2 = 1 (dimensionless "
        "comparisons). Physical amplitudes carry field units instead.",
        ("ref_voelz2011",),
    ),
    # --- units -----------------------------------------------------------
    "units_si": Convention(
        "units_si",
        "unit_system",
        "SI units via Pint",
        "All physical quantities carry explicit Pint units (m, s, V/m, "
        "W/m^2, ...). No unitless magic numbers in ModelSpecs.",
        ("ref_goodman2017",),
    ),
}

STOV_DEFAULT_CONVENTION_IDS: tuple[str, ...] = (
    "coord_xyt_z_prop",
    "ft_space_exp_neg",
    "ft_time_exp_pos",
    "harmonic_exp_neg_iwt",
    "phase_sign_stov_xt",
    "units_si",
)

SPATIAL_DEFAULT_CONVENTION_IDS: tuple[str, ...] = (
    "coord_xy_z_prop",
    "ft_space_exp_neg",
    "harmonic_exp_neg_iwt",
    "phase_sign_oam_xy",
    "units_si",
)

KNOWN_SOURCE_IDS: frozenset[str] = frozenset(
    {
        "ref_goodman2017",
        "ref_voelz2011",
        "ref_chong2020",
        "ref_bliokh2012",
        "ref_andrews2005",
        "ref_lane1992",
        "ref_schmidt2010",
    }
)


def get_convention(convention_id: str) -> Convention:
    try:
        return CONVENTION_REGISTRY[convention_id]
    except KeyError as exc:
        raise SchemaError(f"unknown convention_id: {convention_id!r}") from exc


def validate_convention_ids(convention_ids: list[str] | tuple[str, ...]) -> list[str]:
    """Return unknown convention ids (empty = all valid)."""
    return [c for c in convention_ids if c not in CONVENTION_REGISTRY]


def require_convention_categories(
    convention_ids: list[str] | tuple[str, ...],
    required_categories: tuple[str, ...],
) -> list[str]:
    """Return missing categories for a set of convention ids."""
    present = {get_convention(c).category for c in convention_ids}
    return [cat for cat in required_categories if cat not in present]
