"""Shared test object factories (imported by test modules)."""

from __future__ import annotations

from stov_scientist.physics.fields import make_axis, stov_vortex
from stov_scientist.schemas import (
    AcceptancePolicy,
    ConvergenceRule,
    ResearchProblem,
    ScientificModelSpec,
    SimulationSpec,
    ValidityDomain,
)

POLICY = AcceptancePolicy(
    policy_id="p-1",
    convergence_rules=[
        ConvergenceRule(
            rule_id="rule-1", metric="charge_refinement", target=0.05, min_refinements=1
        )
    ],
)


def make_model(**overrides) -> ScientificModelSpec:
    data = dict(
        model_id="model-stov",
        name="STOV linear vortex",
        model_type="ANALYTICAL",
        equations=[
            {
                "equation_id": "eq-1",
                "symbolic_form": "E = A * (x + I*c0*t) * exp(-x**2/wx**2 - t**2/wt**2)",
                "status": "VALIDATED",
                "source_ids": ["ref_chong2020"],
            }
        ],
        independent_variables=["x", "t"],
        dependent_variables=["E"],
        symbols={
            "x": "m",
            "t": "s",
            "c0": "m/s",
            "wx": "m",
            "wt": "s",
            "wavelength": "m",
            "propagation_distance": "m",
            "carrier_omega": "rad/s",
            "A": "V/m",
            "E": "V/m",
        },
        coordinate_system="coord-xyt",
        convention_ids=["coord_xyt_z_prop", "phase_sign_stov_xt", "units_si"],
        validity_domain=ValidityDomain(
            domain_id="d-1",
            description="linear STOV",
            parameter_ranges={"wx": (0.0, 5e-3), "wt": (0.0, 1e-11)},
        ),
        initial_conditions=[
            {"ic_id": "ic-1", "variable": "E", "expression": "E0", "units": "V/m"}
        ],
        boundary_conditions=[
            {"bc_id": "bc-1", "region": "grid", "kind": "PERIODIC", "expression": "FFT"}
        ],
    )
    data.update(overrides)
    return ScientificModelSpec(**data)


def make_spec(model: ScientificModelSpec, **overrides) -> SimulationSpec:
    data = dict(
        simulation_id="sim-stov",
        model_id=model.model_id,
        domain="free space",
        grid={
            "grid_id": "g-1",
            "kind": "x-t",
            "axes": ["x", "t"],
            "shape": [128, 128],
            "spacing": {"x": 3e-5, "t": 1.6e-13},
            "domain_extent": {"x": 128 * 3e-5, "t": 128 * 1.6e-13},
            "units": {"x": "m", "t": "s"},
        },
        parameters={
            "wx": 1e-3,
            "wt": 3.3356e-12,
            "wavelength": 800e-9,
            "propagation_distance": 0.05,
            "carrier_omega": 2.3546e15,
            "field_kind": "stov_vortex_xt",
        },
        random_seed=0,
        ensemble_size=1,
        convergence_plan={
            "strategy": "GRID_REFINEMENT",
            "refinement_levels": [0, 1],
            "target_observable": "energy",
            "acceptance_rule": "rule-1",
        },
    )
    data.update(overrides)
    return SimulationSpec(**data)


def make_problem(problem_id: str = "prob-test") -> ResearchProblem:
    return ResearchProblem(
        problem_id=problem_id,
        title="STOV propagation",
        research_question="How does a spatiotemporal vortex propagate in vacuum?",
        system_under_study="STOV pulse",
        scope="vacuum",
        excluded_scope="",
        target_observables=["topological_charge"],
    )


def make_vortex_phase(n=128, charge=1):
    """Complex STOV vortex field (ratio-method charge measurement — exact
    for arbitrary integer charges, immune to wrapped-phase cut issues)."""
    x = make_axis(0.0, 2e-3, n)
    t = make_axis(0.0, 2e-12, n)
    return stov_vortex(x, t, 1e-3, 1e-12, charge=charge).values
