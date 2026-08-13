"""STOV Benchmark B01-B10 (spec PHASE 20). Deterministic, offline."""

from __future__ import annotations

import numpy as np
import pytest

from stov_scientist.control.routers import classify_contradiction
from stov_scientist.errors import SchemaError, ValidationError
from stov_scientist.physics.topology import estimate_topological_charge
from stov_scientist.schemas import ContradictionType, ConvergenceRule, EvidenceRecord
from stov_scientist.validators.convergence import check_refinement_sequence
from stov_scientist.validators.evidence import validate_evidence_record
from stov_scientist.validators.sampling import validate_sampling
from stov_scientist.validators.units import parse_unit
from tests.helpers import POLICY, make_model, make_spec, make_vortex_phase

# ---------------------------------------------------------------------------
# B01: known positive topology
# ---------------------------------------------------------------------------


def test_B01_known_positive_topology():
    q = estimate_topological_charge(make_vortex_phase(charge=1))
    assert abs(q - 1.0) < 0.5


# ---------------------------------------------------------------------------
# B02: known negative topology
# ---------------------------------------------------------------------------


def test_B02_known_negative_topology():
    q = estimate_topological_charge(make_vortex_phase(charge=-1))
    assert abs(q + 1.0) < 0.5


# ---------------------------------------------------------------------------
# B03: zero winding
# ---------------------------------------------------------------------------


def test_B03_zero_winding():
    phase = np.zeros((64, 64))
    q = estimate_topological_charge(phase)
    assert abs(q) < 0.5


# ---------------------------------------------------------------------------
# B04: invalid unit
# ---------------------------------------------------------------------------


def test_B04_invalid_unit():
    with pytest.raises(SchemaError):
        parse_unit("furlong_per_fortnight!!")


# ---------------------------------------------------------------------------
# B05: undersampled field rejection
# ---------------------------------------------------------------------------


def test_B05_undersampled_field_rejection():
    model = make_model()
    spec = make_spec(model)
    result, report = validate_sampling(spec, propagation_distance=1e3, wavelength=800e-9)
    assert not result.passed
    assert not report.usable_for_conclusions


# ---------------------------------------------------------------------------
# B06: convergence test
# ---------------------------------------------------------------------------


def test_B06_convergence_test():
    rule = ConvergenceRule(rule_id="b06", metric="m", target=1e-2, min_refinements=1)
    _, converged = check_refinement_sequence({0: 1.0, 1: 1.0001}, rule)
    assert converged.achieved
    _, not_converged = check_refinement_sequence({0: 1.0, 1: 1.5}, rule)
    assert not not_converged.achieved


# ---------------------------------------------------------------------------
# B07: fake/invalid evidence provenance
# ---------------------------------------------------------------------------


def test_B07_fake_invalid_evidence_provenance():
    # fabricated record: no search boundary, no identifier
    fake = EvidenceRecord(
        evidence_id="ev-fake",
        source_type="JOURNAL",
        source_id="W-fake",
        title="Definitely real paper",
        year=2020,
    )
    result = validate_evidence_record(fake)
    assert not result.passed


# ---------------------------------------------------------------------------
# B08: out-of-validity-domain model
# ---------------------------------------------------------------------------


def test_B08_out_of_validity_domain_model(simulation_runner):
    model = make_model()
    spec = make_spec(model)
    spec.parameters["wx"] = 10.0  # far outside the domain
    with pytest.raises(ValidationError):
        simulation_runner.run(model, spec, policy=POLICY)


# ---------------------------------------------------------------------------
# B09: numerical failure must not become physical contradiction
# ---------------------------------------------------------------------------


def test_B09_numerical_failure_not_physical_contradiction():
    kind = classify_contradiction(run_status="NUMERICAL_FAILURE", prediction_mismatch=True)
    assert kind is ContradictionType.NUMERICAL_FAILURE
    assert kind is not ContradictionType.PHYSICAL_CONTRADICTION


# ---------------------------------------------------------------------------
# B10: search failure must not become "no literature exists"
# ---------------------------------------------------------------------------


def test_B10_search_failure_not_zero_literature():
    from stov_scientist.literature.search import search_literature

    class FailingClient:
        def search(self, query, max_results=10):
            raise RuntimeError("database unreachable")

        def close(self):
            pass

    outcome = search_literature(
        ["stov"],
        ["openalex"],
        campaign_id="cmp-b10",
        evidence_set_id="es-1",
        boundary_id="b10",
        clients={"openalex": FailingClient()},
    )
    # retrieval status documents the failure — never ZERO_LITERATURE
    assert outcome.boundary.retrieval_status.value == "PARTIAL_RETRIEVAL"
    assert outcome.retrieval_errors
