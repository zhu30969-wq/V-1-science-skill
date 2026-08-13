"""Deterministic ScientificModelSpec templates (spec §20 pipeline).

The STOV linear-vortex template carries the full provenance chain:
primary source (Chong et al. 2020) -> convention registry -> transcribed
equation -> unit/dim check -> limiting cases (unit-tested) -> template.

Any model built outside this chain MUST carry status CANDIDATE_MODEL.
"""

from __future__ import annotations

from stov_scientist.physics.conventions import STOV_DEFAULT_CONVENTION_IDS
from stov_scientist.schemas import (
    BoundaryCondition,
    Equation,
    EquationStatus,
    InitialCondition,
    Invariant,
    ModelType,
    ProvenanceRecord,
    ScientificModelSpec,
    SolverRequirement,
    ValidityDomain,
)


def stov_linear_vortex_model(
    model_id: str = "model-stov-linear-vortex",
    *,
    domain_x: tuple[float | None, float | None] = (None, None),
    domain_t: tuple[float | None, float | None] = (None, None),
    domain_wavelength: tuple[float | None, float | None] = (None, None),
    domain_z: tuple[float | None, float | None] = (0.0, None),
) -> ScientificModelSpec:
    """Validated STOV linear-vortex ansatz model (Chong et al. 2020 form).

    E(x, t) = (x + i sgn(l) t)^|l| exp(-x^2/wx^2 - t^2/wt^2),
    phase atan2(sgn(l) t, x) for |l| = 1, in the (x, t) transverse plane,
    harmonic time dependence exp(-i omega t), propagation +z.
    """
    return ScientificModelSpec(
        model_id=model_id,
        name="STOV linear spatiotemporal vortex (linear ansatz)",
        model_type=ModelType.ANALYTICAL,
        equations=[
            Equation(
                equation_id=f"{model_id}-eq-field",
                symbolic_form=(
                    "E = A * (x + I*sgn*c0*t)**abs(l) "
                    "* exp(-x**2/wx**2 - t**2/wt**2)"
                ),
                terms={
                    "(x + I sgn c0 t)^|l|": (
                        "vortex factor in the spatiotemporal plane; c0·t is the "
                        "time-coordinate converted to length so the sum is "
                        "dimensionally consistent; phase atan2(c0·t, x) — same "
                        "winding as atan2(t, x) under the positive scaling c0"
                    ),
                    "exp(...)": "Gaussian envelope with 1/e widths wx (space), wt (time)",
                },
                derivation_source="Chong et al., Nature Photonics 14, 350 (2020)",
                source_ids=["ref_chong2020"],
                status=EquationStatus.VALIDATED,
            ),
        ],
        independent_variables=["x", "t"],
        dependent_variables=["E"],
        symbols={
            "x": "m",
            "t": "s",
            "c0": "m/s",
            "A": "V/m",
            "wx": "m",
            "wt": "s",
            "wavelength": "m",
            "propagation_distance": "m",
            "carrier_omega": "rad/s",
            "l": "dimensionless",
            "E": "V/m",
            "sgn": "dimensionless",
        },
        units={"field": "V/m"},
        coordinate_system="coord-xyt",
        convention_ids=list(STOV_DEFAULT_CONVENTION_IDS),
        physical_assumptions=[
            "linear (paraxial envelope) scalar field",
            "vacuum propagation, no dispersion beyond k_z(omega)",
            "monochromatic carrier with slowly varying envelope",
            "isotropic spatiotemporal envelope: c0*wt = wx — an anisotropic "
            "envelope vortex splits into a +1/-1 vortex pair under free "
            "propagation (measured by the platform's singularity detection)",
        ],
        numerical_assumptions=[
            "uniform Cartesian grid in (x, t)",
            "periodic FFT boundary conditions",
        ],
        initial_conditions=[
            InitialCondition(
                ic_id=f"{model_id}-ic",
                variable="E",
                expression="(x + I*sgn*t)**abs(l) * exp(-x**2/wx**2 - t**2/wt**2)",
                units="V/m",
            )
        ],
        boundary_conditions=[
            BoundaryCondition(
                bc_id=f"{model_id}-bc",
                region="grid boundary (x, t)",
                kind="PERIODIC",
                expression="FFT-periodic",
            )
        ],
        validity_domain=ValidityDomain(
            domain_id=f"{model_id}-domain",
            description=(
                "Linear STOV ansatz: |l| = 1 vortex in the (x, t) plane; "
                "valid for paraxial propagation over distances where the "
                "angular-spectrum transfer function is alias-free "
                "(z <= N dx^2 / lambda per transverse axis, Voelz 2011)."
            ),
            parameter_ranges={
                "wx": domain_x,
                "wt": domain_t,
                "wavelength": domain_wavelength,
                "propagation_distance": domain_z,
            },
            spatial_domain="x in [-Nx dx/2, Nx dx/2]",
            temporal_domain="t in [-Nt dt/2, Nt dt/2]",
            regime_constraints=[
                "paraxial: envelope widths >> wavelength",
                "alias-free propagation distance bound",
                "isotropic spatiotemporal envelope (c0*wt = wx) for stable "
                "vortex propagation; anisotropic envelopes split into vortex "
                "pairs — a real propagation effect, not a numerical artifact",
            ],
            applicability_notes=(
                "Analytical template for topology/observable studies. NOT a "
                "nonlinear or dispersive model."
            ),
        ),
        invariants=[
            Invariant(
                invariant_id=f"{model_id}-inv-energy",
                name="energy conservation in vacuum propagation",
                expression="sum(|E|^2) = const",
                checked_by="physics-propagation-energy-conservation",
            ),
        ],
        predicted_observables=["intensity", "phase", "topological_charge"],
        falsification_conditions=[
            "topological charge measured on the (x,t) phase differs from l "
            "outside numerical uncertainty"
        ],
        solver_requirements=[
            SolverRequirement(
                requirement_id=f"{model_id}-req-fft",
                kind="FFT_GRID",
                note="uniform (x, t) grid for FFT-based propagation",
            )
        ],
        source_ids=["ref_chong2020", "ref_goodman2017", "ref_voelz2011"],
        provenance=ProvenanceRecord(source_ids=["ref_chong2020", "ref_goodman2017"]),
    )
