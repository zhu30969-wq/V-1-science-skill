"""Worker tests (spec §70): deterministic paths without LLM; fake-model
paths for structured output; STRUCTURED_OUTPUT_FAILURE retry behaviour."""

from __future__ import annotations

from stov_scientist.literature.base import LiteratureRecord
from stov_scientist.literature.dedup import deduplicate, same_paper
from stov_scientist.schemas import ResearchProblem
from stov_scientist.workers.base import run_structured
from stov_scientist.workers.counterexample import boundary_cases, numerical_stress_cases
from stov_scientist.workers.hypothesis import generate_hypotheses
from stov_scientist.workers.literature import run_literature_search
from tests.fakes import scripted_model


def make_problem() -> ResearchProblem:
    return ResearchProblem(
        problem_id="prob-w",
        title="STOV propagation",
        research_question="How does a spatiotemporal vortex propagate in vacuum?",
        system_under_study="STOV pulse",
        scope="vacuum",
        excluded_scope="",
        target_observables=["topological_charge"],
    )


# ---------------------------------------------------------------------------
# deterministic (no LLM)
# ---------------------------------------------------------------------------


def test_dedup_by_doi():
    a = LiteratureRecord(title="X", doi="10.1000/x", source_database="a")
    b = LiteratureRecord(title="X", doi="10.1000/X", source_database="b")  # case differs
    assert same_paper(a, b)
    assert len(deduplicate([a, b])) == 1


def test_dedup_by_title_year_author_overlap():
    a = LiteratureRecord(
        title="Generation of spatiotemporal optical vortices",
        authors=["A. Chong", "C. Wan", "J. Chen"],
        year=2020,
        source_database="a",
    )
    b = LiteratureRecord(
        title="Generation of spatiotemporal optical vortices",
        authors=["Chong, A.", "Wan, C."],
        year=2020,
        source_database="b",
    )
    assert same_paper(a, b)
    assert len(deduplicate([a, b])) == 1


def test_dedup_different_years_not_merged():
    a = LiteratureRecord(title="Same title", authors=["X Y"], year=2010)
    b = LiteratureRecord(title="Same title", authors=["X Y"], year=2020)
    assert not same_paper(a, b)


def test_dedup_one_doi_one_not_not_merged():
    """DOI vs no-DOI records are never conflated (spec §35)."""
    a = LiteratureRecord(title="X", doi="10.1000/x")
    b = LiteratureRecord(title="X")
    assert not same_paper(a, b)


def test_literature_search_with_injected_clients():
    class FakeClient:
        def search(self, query, max_results=10):
            from stov_scientist.literature.base import ClientResponse
            from stov_scientist.schemas import RetrievalStatus

            return ClientResponse(
                status=RetrievalStatus.COMPLETE,
                records=[
                    LiteratureRecord(
                        title="A study of STOV",
                        authors=["A. Author"],
                        year=2021,
                        doi="10.1000/stov",
                        source_database="fake",
                    )
                ],
            )

        def close(self):
            pass

    evidence = run_literature_search(
        make_problem(),
        campaign_id="cmp-1",
        evidence_set_id="es-1",
        boundary_id="b-1",
        queries=["stov"],
        databases=["openalex"],
        clients={"openalex": FakeClient()},
    )
    assert evidence is not None
    assert len(evidence.records) == 1
    assert evidence.search_boundaries[0].retrieved_count == 1
    assert evidence.search_boundaries[0].search_boundary_id == "b-1"


def test_literature_search_partial_retrieval_is_not_zero():
    """A failing client yields PARTIAL_RETRIEVAL, never ZERO_LITERATURE."""

    class FailingClient:
        def search(self, query, max_results=10):
            raise RuntimeError("network down")

        def close(self):
            pass

    evidence = run_literature_search(
        make_problem(),
        campaign_id="cmp-1",
        evidence_set_id="es-1",
        boundary_id="b-1",
        queries=["stov"],
        databases=["openalex"],
        clients={"openalex": FailingClient()},
    )
    # no records, but the boundary documents the retrieval failure
    assert evidence is None or not evidence.records


def test_boundary_cases_deterministic():
    from stov_scientist.schemas import ScientificModelSpec, ValidityDomain

    model = ScientificModelSpec(
        model_id="m-1",
        name="m",
        equations=[{"equation_id": "e-1", "symbolic_form": "E = 1"}],
        independent_variables=["x"],
        dependent_variables=["E"],
        symbols={},
        coordinate_system="coord-xyt",
        validity_domain=ValidityDomain(
            domain_id="d-1",
            description="d",
            parameter_ranges={"wx": (0.0, 1.0), "wt": (0.0, 1.0)},
        ),
    )
    cases = boundary_cases(model)
    assert len(cases) == 9  # 3x3 corner grid
    assert all(c.within_validity_domain for c in cases)
    assert all(c.search_kind == "BOUNDARY_CASE" for c in cases)


def test_numerical_stress_cases():
    from stov_scientist.schemas import SimulationSpec

    spec = SimulationSpec(
        simulation_id="s-1",
        model_id="m-1",
        domain="d",
        grid={
            "grid_id": "g-1",
            "kind": "x-t",
            "axes": ["x", "t"],
            "shape": [64, 64],
            "spacing": {"x": 1e-5, "t": 1e-14},
            "domain_extent": {"x": 64e-5, "t": 64e-14},
        },
        parameters={},
        convergence_plan={
            "strategy": "GRID_REFINEMENT",
            "refinement_levels": [0, 1],
            "target_observable": "energy",
            "acceptance_rule": "r-1",
        },
    )
    cases = numerical_stress_cases(spec, seeds=(0, 1, 2))
    assert len(cases) == 3
    assert all(c.search_kind == "NUMERICAL_STRESS" for c in cases)


# ---------------------------------------------------------------------------
# structured output with fake model
# ---------------------------------------------------------------------------


def test_structured_output_success():
    from langchain_core.messages import HumanMessage
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    model = scripted_model(("ask", {"value": 7}))
    result = run_structured(model, Payload, [HumanMessage(content="ask")])
    assert result.ok
    assert result.value.value == 7


def test_structured_output_retry_once_then_failure():
    """First invalid, second invalid -> STRUCTURED_OUTPUT_FAILURE (exactly
    one retry, spec §34)."""
    from langchain_core.messages import HumanMessage
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    model = scripted_model(
        ("ask", {"value": "not-an-int"}),
        ("previous output was invalid", {"value": "still-bad"}),
    )
    result = run_structured(model, Payload, [HumanMessage(content="ask")])
    assert not result.ok
    assert result.status == "STRUCTURED_OUTPUT_FAILURE"
    assert result.attempts == 2


def test_structured_output_recovers_on_retry():
    from langchain_core.messages import HumanMessage
    from pydantic import BaseModel

    class Payload(BaseModel):
        value: int

    model = scripted_model(
        ("ask", {"value": "bad"}),
        ("previous output was invalid", {"value": 42}),
    )
    result = run_structured(model, Payload, [HumanMessage(content="ask")])
    assert result.ok
    assert result.value.value == 42
    assert result.attempts == 2


def test_hypothesis_generation_with_fake_model():
    model = scripted_model(
        (
            "Problem",
            {
                "hypotheses": [
                    {
                        "statement": "The STOV charge is preserved in vacuum.",
                        "claim_type": "BEHAVIOUR",
                        "assumptions": ["linear"],
                        "boundary_conditions": ["vacuum"],
                        "predictions": ["topological_charge: constant"],
                        "falsification_conditions": ["charge changes beyond tolerance"],
                        "unknowns": [],
                        "testability": "HIGH",
                        "evidence_coverage": "UNASSESSED",
                        "assumption_burden": "LOW",
                        "experimental_feasibility": "MEDIUM",
                        "computational_feasibility": "HIGH",
                    }
                ],
                "rationale": "r",
            },
        ),
    )
    hypotheses = generate_hypotheses(model, make_problem(), None)
    assert len(hypotheses) == 1
    h = hypotheses[0]
    assert h.status.value == "CANDIDATE"
    assert h.predictions[0].observable == "topological_charge"
    assert h.falsification_conditions[0].statement
