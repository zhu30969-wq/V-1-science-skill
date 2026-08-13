"""Deterministic validator tests (spec §67): units, dimensions, symbols,
limits, boundary, convergence, evidence, topology validators."""

from __future__ import annotations

import pytest

from stov_scientist.errors import SchemaError
from stov_scientist.physics.fields import make_axis, stov_vortex
from stov_scientist.schemas import (
    VALIDATION_LEVEL_ORDER,
    AcceptancePolicy,
    ConvergenceRule,
    EvidenceRecord,
    ScientificModelSpec,
    SimulationSpec,
    ValidityDomain,
)
from stov_scientist.validators import ValidatorContext, run_validators
from stov_scientist.validators.convergence import check_refinement_sequence
from stov_scientist.validators.dimensions import validate_dimensions
from stov_scientist.validators.evidence import validate_evidence_record
from stov_scientist.validators.limits import validate_parameter_limits
from stov_scientist.validators.sampling import validate_sampling
from stov_scientist.validators.symbolic import (
    check_algebraic_equivalence,
    evaluate_limiting_expression,
    validate_symbol_coverage,
)
from stov_scientist.validators.topology import (
    validate_singularity_detection,
    validate_topological_charge,
)
from stov_scientist.validators.units import parse_unit, same_dimensionality


def make_model(**overrides) -> ScientificModelSpec:
    data = dict(
        model_id="model-valid",
        name="validated linear model",
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
            domain_id="domain-1",
            description="linear STOV domain",
            parameter_ranges={"wx": (0.0, 1.0), "wt": (0.0, 1.0)},
        ),
        initial_conditions=[
            {"ic_id": "ic-1", "variable": "E", "expression": "E0(x,t)", "units": "V/m"}
        ],
        boundary_conditions=[
            {"bc_id": "bc-1", "region": "grid", "kind": "PERIODIC", "expression": "FFT"}
        ],
        solver_requirements=[{"requirement_id": "r-1", "kind": "FFT_GRID", "note": ""}],
    )
    data.update(overrides)
    return ScientificModelSpec(**data)


def make_spec(model: ScientificModelSpec, **overrides) -> SimulationSpec:
    data = dict(
        simulation_id="sim-valid",
        model_id=model.model_id,
        domain="free space",
        grid={
            "grid_id": "g-1",
            "kind": "x-t",
            "axes": ["x", "t"],
            "shape": [128, 128],
            "spacing": {"x": 3e-5, "t": 3e-14},
            "domain_extent": {"x": 128 * 3e-5, "t": 128 * 3e-14},
            "units": {"x": "m", "t": "s"},
        },
        parameters={
            "wx": 1e-3,
            "wt": 1e-12,
            "wavelength": 800e-9,
            "propagation_distance": 0.05,
            "carrier_omega": 2.3546e15,
            "field_kind": "stov_vortex_xt",
        },
        convergence_plan={
            "strategy": "GRID_REFINEMENT",
            "refinement_levels": [0, 1],
            "target_observable": "topological_charge",
            "acceptance_rule": "rule-1",
        },
    )
    data.update(overrides)
    return SimulationSpec(**data)


# ---------------------------------------------------------------------------
# units
# ---------------------------------------------------------------------------


def test_pint_unit_parse():
    assert str(parse_unit("V/m")) == "volt / meter"


def test_unit_mismatch_rejection():
    """Unit mismatch is rejected - no string comparison (spec section 23)."""
    assert not same_dimensionality("m", "s")
    assert same_dimensionality("km", "m")
    with pytest.raises(SchemaError):
        parse_unit("not_a_unit!!")


def test_model_units_validator_passes_and_fails():
    model = make_model()
    context = ValidatorContext(models={model.model_id: model})
    report = run_validators(model, context)
    assert report.passed
    bad = make_model(symbols={"x": "furlong_per_fortnight!!"})
    report = run_validators(bad, ValidatorContext(models={bad.model_id: bad}))
    assert not report.passed


# ---------------------------------------------------------------------------
# dimensions
# ---------------------------------------------------------------------------


def test_dimensionally_consistent_model_passes():
    report = validate_dimensions(make_model())
    assert report.passed


def test_dimensional_mismatch_caught():
    """exp() argument with dimensions is flagged."""
    model = make_model(
        equations=[
            {
                "equation_id": "eq-bad",
                "symbolic_form": "E = A * exp(-x)",  # exp(-x) with x in meters
                "status": "CANDIDATE_MODEL",
            }
        ],
        symbols={"x": "m", "E": "V/m", "A": "V/m"},
    )
    report = validate_dimensions(model)
    assert not report.passed
    assert any("not dimensionless" in p for p in report.details["problems"])


# ---------------------------------------------------------------------------
# symbols
# ---------------------------------------------------------------------------


def test_symbol_coverage_undeclared_symbol():
    model = make_model(
        equations=[
            {
                "equation_id": "eq-1",
                "symbolic_form": "E = alpha * exp(-x**2)",
                "status": "CANDIDATE_MODEL",
            }
        ]
    )
    report = validate_symbol_coverage(model)
    assert not report.passed
    assert any("alpha" in p for p in report.details["per_equation"]["eq-1"])


def test_algebraic_equivalence():
    from stov_scientist.schemas import Equation

    a = Equation(equation_id="e-a", symbolic_form="E = x**2 + 2*x + 1")
    b = Equation(equation_id="e-b", symbolic_form="E = (x + 1)**2")
    assert check_algebraic_equivalence(a, b)
    c = Equation(equation_id="e-c", symbolic_form="E = x**2 + 1")
    assert not check_algebraic_equivalence(a, c)


def test_limiting_expression():
    result = evaluate_limiting_expression("(x + I*t)**1 * exp(-x**2/wx**2)", "t", 0)
    assert "t" not in result.replace("**", "").split("*")[0].lower() or "I" in result


# ---------------------------------------------------------------------------
# limits
# ---------------------------------------------------------------------------


def test_parameter_outside_domain_rejected():
    model = make_model()
    spec = make_spec(model, parameters={"wx": 5.0, "wt": 1e-12, "field_kind": "x"})
    result = validate_parameter_limits(spec, model)
    assert not result.passed
    assert any("above domain upper bound" in p for p in result.details["problems"])


def test_parameter_inside_domain_passes():
    model = make_model()
    spec = make_spec(model)
    result = validate_parameter_limits(spec, model)
    assert result.passed


# ---------------------------------------------------------------------------
# convergence (no global thresholds �?policy-driven, spec §29)
# ---------------------------------------------------------------------------


def test_convergence_uses_campaign_rule():
    rule = ConvergenceRule(rule_id="r-1", metric="m", target=0.05, min_refinements=1)
    result, convergence = check_refinement_sequence({0: 1.0, 1: 1.001}, rule)
    assert result.passed and convergence.achieved
    result, convergence = check_refinement_sequence({0: 1.0, 1: 1.5}, rule)
    assert not result.passed and not convergence.achieved


def test_convergence_requires_min_refinements():
    rule = ConvergenceRule(rule_id="r-1", metric="m", target=0.5, min_refinements=2)
    result, convergence = check_refinement_sequence({0: 1.0, 1: 1.0}, rule)
    assert not result.passed
    assert convergence.verdict == "INSUFFICIENT_REFINEMENTS"


def test_convergence_rejects_nonconsecutive_levels():
    rule = ConvergenceRule(rule_id="r-1", metric="m", target=0.5, min_refinements=1)
    with pytest.raises(SchemaError):
        check_refinement_sequence({0: 1.0, 2: 1.0}, rule)


# ---------------------------------------------------------------------------
# sampling
# ---------------------------------------------------------------------------


def test_sampling_valid_grid_passes():
    model = make_model()
    spec = make_spec(model)
    result, report = validate_sampling(spec, propagation_distance=0.05, wavelength=800e-9)
    assert result.passed
    assert report.usable_for_conclusions


def test_sampling_undersampled_carrier_rejected():
    model = make_model()
    spec = make_spec(model)
    result, _ = validate_sampling(spec, carrier_frequencies={"x": 1e9})
    assert not result.passed


def test_sampling_extent_mismatch_rejected():
    model = make_model()
    spec = make_spec(model, grid={**make_spec(model).grid.model_dump(), "domain_extent": {"x": 1.0, "t": 1e-9}})
    result, _ = validate_sampling(spec)
    assert not result.passed


def test_sampling_propagation_distance_bound():
    model = make_model()
    spec = make_spec(model)
    # far beyond alias-free bound -> rejected
    result, _ = validate_sampling(spec, propagation_distance=1e3, wavelength=800e-9)
    assert not result.passed


# ---------------------------------------------------------------------------
# topology validators
# ---------------------------------------------------------------------------


def test_topology_validator_charge_match():
    x = make_axis(0.0, 2e-3, 128)
    t = make_axis(0.0, 2e-12, 128)
    values = stov_vortex(x, t, 1e-3, 1e-12, charge=1).values
    result = validate_topological_charge(values, expected_charge=1)
    assert result.passed
    result = validate_topological_charge(values, expected_charge=-1)
    assert not result.passed


def test_singularity_validator():
    x = make_axis(0.0, 2e-3, 128)
    t = make_axis(0.0, 2e-12, 128)
    phase = stov_vortex(x, t, 1e-3, 1e-12, charge=1).phase()
    result = validate_singularity_detection(phase, expected_singularities=1, expected_charge_sum=1)
    assert result.passed


# ---------------------------------------------------------------------------
# evidence
# ---------------------------------------------------------------------------


def test_evidence_record_missing_boundary_fails():
    record = EvidenceRecord(
        evidence_id="ev-x",
        source_type="JOURNAL",
        source_id="s1",
        title="t",
        identifiers={"doi": "10.0/x"},
    )
    result = validate_evidence_record(record)
    assert not result.passed


def test_evidence_record_complete_passes():
    record = EvidenceRecord(
        evidence_id="ev-x",
        source_type="JOURNAL",
        source_id="s1",
        title="t",
        identifiers={"doi": "10.0/x"},
        search_boundary_id="b-1",
    )
    result = validate_evidence_record(record)
    assert result.passed


# ---------------------------------------------------------------------------
# runner ordering
# ---------------------------------------------------------------------------


def test_validator_order_stops_at_first_failure():
    model = make_model(
        symbols={"x": "furlong_per_fortnight!!", "t": "s", "wx": "m", "wt": "s", "E": "V/m"}
    )
    report = run_validators(model, ValidatorContext(models={model.model_id: model}))
    assert not report.passed
    assert report.stop_level is not None
    order = list(VALIDATION_LEVEL_ORDER)
    # SCHEMA and UNITS ran; failure at UNITS stops before DIMENSIONS
    assert report.stop_level.value == "UNITS"
    assert order.index(report.stop_level.value) <= order.index("DIMENSIONS")


def test_acceptance_policy_forbids_universal_score():
    """AcceptancePolicy has no 'physics_score' field (spec §44)."""
    policy = AcceptancePolicy(policy_id="p-1")
    assert not hasattr(policy, "physics_score")
