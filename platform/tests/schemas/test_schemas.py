"""Schema tests (spec §66): valid objects, missing required, bad enum,
invalid references, serialization round trips."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from stov_scientist.schemas import (
    EvidenceRecord,
    EvidenceRelation,
    EvidenceSet,
    HypothesisCandidate,
    HypothesisStatus,
    ResearchProblem,
    ScientificModelSpec,
    SearchBoundary,
    SimulationSpec,
    ValidityDomain,
)


def make_problem() -> ResearchProblem:
    return ResearchProblem(
        problem_id="prob-test",
        title="Test STOV question",
        research_question="How does a STOV vortex propagate in vacuum?",
        system_under_study="STOV pulse",
        scope="vacuum propagation",
        excluded_scope="turbulence",
        target_observables=["topological_charge"],
    )


def make_model() -> ScientificModelSpec:
    return ScientificModelSpec(
        model_id="model-test",
        name="test model",
        model_type="ANALYTICAL",
        equations=[
            {
                "equation_id": "model-test-eq1",
                "symbolic_form": "E = A * exp(-x**2/wx**2)",
                "status": "CANDIDATE_MODEL",
            }
        ],
        independent_variables=["x"],
        dependent_variables=["E"],
        symbols={"A": "V/m", "x": "m", "wx": "m", "E": "V/m"},
        coordinate_system="coord-xyt",
        convention_ids=["coord_xyt_z_prop", "units_si"],
        validity_domain=ValidityDomain(
            domain_id="model-test-domain",
            description="test domain",
            parameter_ranges={"wx": (0.0, None)},
        ),
    )


def make_evidence_record(evidence_id: str = "ev-1") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="JOURNAL",
        source_id="W123",
        title="A real study",
        year=2020,
        identifiers={"doi": "10.1000/example"},
        search_boundary_id="boundary-1",
        relation=EvidenceRelation.SUPPORT,
    )


# ---------------------------------------------------------------------------
# valid objects
# ---------------------------------------------------------------------------


def test_valid_problem():
    p = make_problem()
    assert p.problem_id == "prob-test"
    assert p.kind == "MIXED_THEORY_SIMULATION"


def test_valid_model_and_serialization():
    m = make_model()
    dumped = m.model_dump_json()
    loaded = ScientificModelSpec.model_validate_json(dumped)
    assert loaded.model_id == m.model_id
    assert loaded.validity_domain.domain_id == "model-test-domain"


def test_evidence_record_roundtrip():
    record = make_evidence_record()
    assert EvidenceRecord.model_validate_json(record.model_dump_json()) == record


# ---------------------------------------------------------------------------
# missing required
# ---------------------------------------------------------------------------


def test_problem_requires_question():
    with pytest.raises(PydanticValidationError):
        ResearchProblem(problem_id="p-x", title="t")  # missing research_question


def test_model_requires_validity_domain():
    with pytest.raises(PydanticValidationError):
        ScientificModelSpec(
            model_id="m-x",
            name="m",
            equations=[{"equation_id": "e1", "symbolic_form": "E = 0"}],
            independent_variables=["x"],
            dependent_variables=["E"],
            symbols={},
            coordinate_system="coord-xyt",
        )


def test_model_requires_equations():
    with pytest.raises(PydanticValidationError):
        ScientificModelSpec(
            model_id="m-x",
            name="m",
            equations=[],
            independent_variables=["x"],
            dependent_variables=["E"],
            symbols={},
            coordinate_system="coord-xyt",
            validity_domain=ValidityDomain(domain_id="d-1", description="d"),
        )


# ---------------------------------------------------------------------------
# bad enum
# ---------------------------------------------------------------------------


def test_bad_hypothesis_status_rejected():
    with pytest.raises(PydanticValidationError):
        HypothesisCandidate(
            hypothesis_id="h-1",
            statement="x",
            status="PROVEN",  # forbidden vocabulary
        )


def test_hypothesis_statuses_are_the_scientific_vocabulary():
    for status in HypothesisStatus:
        h = HypothesisCandidate(hypothesis_id="h-1", statement="x", status=status)
        assert h.status is status


def test_bad_evidence_relation_rejected():
    with pytest.raises(PydanticValidationError):
        EvidenceRecord.model_validate(
            {**make_evidence_record().model_dump(), "relation": "PROVES"}
        )


# ---------------------------------------------------------------------------
# invalid references
# ---------------------------------------------------------------------------


def test_bad_id_pattern_rejected():
    with pytest.raises(PydanticValidationError):
        ResearchProblem.model_validate(
            {**make_problem().model_dump(), "problem_id": "!!bad id!!"}
        )


def test_search_boundary_required_fields():
    # boundary must be constructible and explicit about scope
    b = SearchBoundary(search_boundary_id="b-1", databases=["openalex"], queries=["q"])
    assert b.retrieved_count == 0
    assert b.language_scope == ["en"]


# ---------------------------------------------------------------------------
# simulation spec
# ---------------------------------------------------------------------------


def test_simulation_spec_requires_convergence_plan():
    with pytest.raises(PydanticValidationError):
        SimulationSpec(
            simulation_id="sim-1",
            model_id="model-test",
            domain="free space",
            grid={
                "grid_id": "g-1",
                "kind": "x-t",
                "axes": ["x", "t"],
                "shape": [64, 64],
                "spacing": {"x": 1e-5, "t": 1e-14},
                "domain_extent": {"x": 64e-5, "t": 64e-14},
            },
            parameters={},
            convergence_plan=None,  # type: ignore[arg-type]
        )


def test_evidence_set_grouping():
    es = EvidenceSet(
        evidence_set_id="es-1",
        campaign_id="campaign-1",
        records=[make_evidence_record("ev-1"), make_evidence_record("ev-2")],
    )
    es.records[1].relation = EvidenceRelation.CONTRADICT
    assert len(es.by_relation(EvidenceRelation.SUPPORT)) == 1
    assert len(es.by_relation(EvidenceRelation.CONTRADICT)) == 1
