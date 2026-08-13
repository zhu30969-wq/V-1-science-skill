"""Deterministic default STOV ontology (used when no LLM is available and
as the baseline for LLM refinement). Every entry carries source_ids."""

from __future__ import annotations

from typing import Any, cast

from stov_scientist.schemas import (
    Concept,
    ConventionSpec,
    CoordinateSystemSpec,
    ModelFamily,
    NumericalAssumption,
    ObservableSpec,
    ParameterSpec,
    PhysicalAssumption,
    ScientificOntology,
    SymbolSpec,
)


def default_stov_ontology(
    ontology_id: str = "ontology-stov-default",
    problem_observables: list[str] | None = None,
) -> ScientificOntology:
    concepts = [
        Concept(
            concept_id="c-stov",
            name="Space-Time Optical Vortex",
            definition=(
                "Optical pulse whose phase winds in the spatiotemporal "
                "(x, t) plane, carrying transverse orbital angular momentum "
                "(Chong et al. 2020)."
            ),
            source_ids=["ref_chong2020"],
        ),
        Concept(
            concept_id="c-angular-spectrum",
            name="Angular spectrum propagation",
            definition="Propagation via spatial/temporal Fourier decomposition (Goodman 2017).",
            source_ids=["ref_goodman2017"],
        ),
        Concept(
            concept_id="c-topological-charge",
            name="Topological charge",
            definition="(1/2pi) phase winding around a singularity in the vortex plane.",
            source_ids=["ref_chong2020"],
        ),
    ]
    symbols = [
        SymbolSpec(symbol_id="s-x", symbol="x", name="transverse position", definition="transverse spatial coordinate in the STOV plane", units="m", source_ids=["ref_chong2020"]),
        SymbolSpec(symbol_id="s-t", symbol="t", name="local time", definition="retarded/local time coordinate in the STOV plane", units="s", source_ids=["ref_chong2020"]),
        SymbolSpec(symbol_id="s-wx", symbol="wx", name="spatial envelope width", definition="1/e width of the Gaussian envelope in x", units="m", source_ids=["ref_chong2020"]),
        SymbolSpec(symbol_id="s-wt", symbol="wt", name="temporal envelope width", definition="1/e width of the Gaussian envelope in t", units="s", source_ids=["ref_chong2020"]),
        SymbolSpec(symbol_id="s-l", symbol="l", name="topological charge", definition="integer phase winding of the vortex", units="dimensionless", source_ids=["ref_chong2020"]),
        SymbolSpec(symbol_id="s-lambda", symbol="lambda", name="wavelength", definition="carrier wavelength", units="m", source_ids=["ref_goodman2017"]),
    ]
    parameters = [
        ParameterSpec(parameter_id="p-wx", symbol="wx", name="spatial envelope width", units="m", source_ids=["ref_chong2020"]),
        ParameterSpec(parameter_id="p-wt", symbol="wt", name="temporal envelope width", units="s", source_ids=["ref_chong2020"]),
        ParameterSpec(parameter_id="p-lambda", symbol="wavelength", name="carrier wavelength", units="m", source_ids=["ref_goodman2017"]),
        ParameterSpec(parameter_id="p-z", symbol="propagation_distance", name="propagation distance", units="m", source_ids=["ref_goodman2017"]),
    ]
    observables = [
        ObservableSpec(
            observable_id="o-intensity",
            symbol="I",
            name="intensity",
            definition="I = |E|^2",
            units="W/m^2",
            source_ids=["ref_goodman2017"],
        ),
        ObservableSpec(
            observable_id="o-phase",
            symbol="phi",
            name="phase",
            definition="phi = arg(E)",
            units="rad",
            source_ids=["ref_chong2020"],
        ),
        ObservableSpec(
            observable_id="o-charge",
            symbol="l",
            name="topological charge",
            definition="(1/2pi) contour integral of d(phi)",
            units="dimensionless",
            measurement_procedure="phase winding analysis (deterministic)",
            source_ids=["ref_chong2020"],
        ),
    ]
    return ScientificOntology(
        ontology_id=ontology_id,
        concepts=concepts,
        relations=[],
        symbols=symbols,
        coordinate_systems=[
            CoordinateSystemSpec(
                system_id="coord-xyt",
                name="STOV spatiotemporal frame",
                axes=["x", "t"],
                origin="vortex center (x=0, t=0)",
                handedness="right",
                source_ids=["ref_chong2020"],
            )
        ],
        conventions=[
            ConventionSpec(
                convention_id=cid,
                category=cast(Any, c.category),
                name=c.name,
                definition=c.definition,
                source_ids=list(c.source_ids),
            )
            for cid in (
                "coord_xyt_z_prop",
                "ft_space_exp_neg",
                "ft_time_exp_pos",
                "harmonic_exp_neg_iwt",
                "phase_sign_stov_xt",
                "units_si",
            )
            for c in [_CONVENTION_LOOKUP[cid]]
        ],
        observables=observables,
        parameters=parameters,
        physical_assumptions=[
            PhysicalAssumption(
                assumption_id="a-linear",
                statement="linear scalar field, vacuum propagation",
                justification="envelope model; nonlinear/dispersive regimes excluded from the template domain",
                source_ids=["ref_chong2020", "ref_goodman2017"],
            )
        ],
        numerical_assumptions=[
            NumericalAssumption(
                assumption_id="a-fft",
                statement="uniform Cartesian grid; FFT-periodic boundaries",
                justification="FFT-based angular spectrum / split-step solvers",
                source_ids=["ref_voelz2011"],
            )
        ],
        model_families=[
            ModelFamily(
                family_id="mf-stov-analytical",
                name="Analytical STOV envelope models",
                description="Closed-form spatiotemporal vortex envelopes (linear ansatz family)",
                applicable_regimes=["paraxial vacuum propagation"],
                source_ids=["ref_chong2020"],
            )
        ],
        known_constraints=[
            "STOV vortex singularity is a phase singularity in the (x, t) plane",
            "topological charge is conserved in free propagation (within numerical validity)",
        ],
        source_ids=["ref_chong2020", "ref_goodman2017", "ref_voelz2011"],
    )


from stov_scientist.physics.conventions import get_convention  # noqa: E402

_CONVENTION_LOOKUP = {
    cid: get_convention(cid)
    for cid in (
        "coord_xyt_z_prop",
        "ft_space_exp_neg",
        "ft_time_exp_pos",
        "harmonic_exp_neg_iwt",
        "phase_sign_stov_xt",
        "units_si",
    )
}
