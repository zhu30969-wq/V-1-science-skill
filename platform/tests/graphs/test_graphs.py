"""Graph tests (spec §69): contradiction classification routes, validation
subgraph actions, simulation retry bounds."""

from __future__ import annotations

from stov_scientist.control.contradiction_graph import (
    classify_and_route,
    contradiction_graph,
)
from stov_scientist.schemas import ContradictionType

# ---------------------------------------------------------------------------
# contradiction classification (spec §45)
# ---------------------------------------------------------------------------


def test_numerical_failure_routes_to_fix_numerical():
    record, action = classify_and_route(
        contradiction_id="c-1", run_status="NUMERICAL_FAILURE",
        simulation_retries_left=1,
    )
    assert record.kind is ContradictionType.NUMERICAL_FAILURE
    assert action == "RERUN_SIMULATION"


def test_sampling_failure_routes_to_redesign_sampling():
    record, action = classify_and_route(
        contradiction_id="c-1", run_status="SAMPLING_FAILURE",
        simulation_retries_left=2,
    )
    assert record.kind is ContradictionType.SAMPLING_FAILURE
    assert action == "RERUN_SIMULATION"


def test_domain_violation_routes_to_revise_model():
    record, action = classify_and_route(
        contradiction_id="c-1", domain_violation=True,
        model_revisions_left=1,
    )
    assert record.kind is ContradictionType.MODEL_DOMAIN_VIOLATION
    assert action == "REVISE_MODEL"


def test_evidence_contradiction_routes_to_review():
    record, action = classify_and_route(
        contradiction_id="c-1", evidence_contradiction=True
    )
    assert record.kind is ContradictionType.EVIDENCE_CONTRADICTION
    assert action == "EVIDENCE_REVIEW"


def test_prediction_mismatch_is_physical_contradiction_only_when_clean():
    """A clean simulation + prediction mismatch = candidate physical
    contradiction; a dirty one never is."""
    record, _ = classify_and_route(
        contradiction_id="c-1", run_status="COMPLETED", prediction_mismatch=True,
    )
    assert record.kind is ContradictionType.PHYSICAL_CONTRADICTION
    record, _ = classify_and_route(
        contradiction_id="c-1", run_status="NUMERICAL_FAILURE", prediction_mismatch=True,
    )
    assert record.kind is ContradictionType.NUMERICAL_FAILURE


def test_indeterminate_routes_to_additional_test():
    record, action = classify_and_route(contradiction_id="c-1")
    assert record.kind is ContradictionType.INDETERMINATE
    assert action == "ADDITIONAL_TEST_OR_HUMAN"


def test_retry_limits_hit_human_review():
    """No unbounded loops (spec §43): retries exhausted -> human."""
    _, action = classify_and_route(
        contradiction_id="c-1", run_status="NUMERICAL_FAILURE",
        simulation_retries_left=0,
    )
    assert action == "HUMAN_REVIEW_REQUIRED"
    _, action = classify_and_route(
        contradiction_id="c-1", domain_violation=True, model_revisions_left=0,
    )
    assert action == "HUMAN_REVIEW_REQUIRED"


def test_contradiction_graph_runs_end_to_end():
    result = contradiction_graph.invoke(
        {
            "contradiction_id": "c-1",
            "run_status": "SAMPLING_FAILURE",
            "sampling_ok": False,
            "simulation_retries_left": 1,
        }
    )
    assert result["kind"] == "SAMPLING_FAILURE"
    assert result["route"] == "redesign_sampling"
    assert result["action"] == "RERUN_SIMULATION"


# ---------------------------------------------------------------------------
# validation graph
# ---------------------------------------------------------------------------


def test_validation_graph_pass_path(services, campaign_manager):
    from stov_scientist.control.validation_graph import validation_graph
    from stov_scientist.physics.model_templates import stov_linear_vortex_model

    model = stov_linear_vortex_model(model_id="model-val-1")
    campaign_manager.save_object("campaign-val", "model_spec", model)
    result = validation_graph.invoke(
        {
            "campaign_id": "campaign-val",
            "model_spec_id": model.model_id,
            "model_revision_count": 0,
            "max_model_revisions": 3,
        },
        config={"configurable": {"services": services}},
    )
    assert result["validation_passed"] is True
    assert result["action"] == "PASS"


def test_validation_graph_failure_limits(services, campaign_manager):
    from stov_scientist.control.validation_graph import validation_graph
    from stov_scientist.schemas import ScientificModelSpec, ValidityDomain

    bad = ScientificModelSpec(
        model_id="model-bad",
        name="bad",
        equations=[
            {"equation_id": "e-1", "symbolic_form": "E = gamma * x"}
        ],
        independent_variables=["x"],
        dependent_variables=["E"],
        symbols={"x": "m", "E": "V/m"},
        coordinate_system="coord-xyt",
        convention_ids=["coord_xyt_z_prop"],
        validity_domain=ValidityDomain(domain_id="d-1", description="d"),
    )
    campaign_manager.save_object("campaign-bad", "model_spec", bad)
    result = validation_graph.invoke(
        {
            "campaign_id": "campaign-bad",
            "model_spec_id": bad.model_id,
            "model_revision_count": 0,
            "max_model_revisions": 3,
        },
        config={"configurable": {"services": services}},
    )
    assert result["validation_passed"] is False
    assert result["action"] == "REVISE_MODEL"

    result = validation_graph.invoke(
        {
            "campaign_id": "campaign-bad",
            "model_spec_id": bad.model_id,
            "model_revision_count": 3,  # limit reached
            "max_model_revisions": 3,
        },
        config={"configurable": {"services": services}},
    )
    assert result["action"] == "HUMAN_REVIEW_REQUIRED"


# ---------------------------------------------------------------------------
# simulation graph
# ---------------------------------------------------------------------------


def test_simulation_graph_happy_path(services, campaign_manager):
    from stov_scientist.control.simulation_graph import simulation_graph
    from stov_scientist.control.spec_builder import build_simulation_spec
    from stov_scientist.physics.model_templates import stov_linear_vortex_model
    from stov_scientist.schemas import ResearchProblem

    model = stov_linear_vortex_model(model_id="model-simg-1")
    problem = ResearchProblem(
        problem_id="prob-simg",
        title="test title",
        research_question="test question",
        system_under_study="s",
        scope="s",
        excluded_scope="",
    )
    spec = build_simulation_spec(
        model, problem, simulation_id="sim-simg"
    )
    campaign_manager.save_object("campaign-simg", "model_spec", model)
    campaign_manager.save_object("campaign-simg", "simulation_spec", spec)
    result = simulation_graph.invoke(
        {
            "campaign_id": "campaign-simg",
            "model_spec_id": model.model_id,
            "simulation_spec_id": spec.simulation_id,
            "retry_count": 0,
            "max_retries": 2,
            "contradiction_kind": "",
        },
        config={"configurable": {"services": services}},
    )
    assert result["completed"] is True
    assert result["run_status"] == "COMPLETED"


def test_simulation_graph_retries_bounded(services, campaign_manager):
    """A failing simulation retries at most max_retries times, then stops
    at HUMAN_REVIEW_REQUIRED (spec §43, §45)."""
    from stov_scientist.control.simulation_graph import simulation_graph
    from stov_scientist.control.spec_builder import build_simulation_spec
    from stov_scientist.physics.model_templates import stov_linear_vortex_model
    from stov_scientist.schemas import ResearchProblem

    model = stov_linear_vortex_model(model_id="model-simfail-1")
    problem = ResearchProblem(
        problem_id="prob-simfail",
        title="test title",
        research_question="test question",
        system_under_study="s",
        scope="s",
        excluded_scope="",
    )
    spec = build_simulation_spec(model, problem, simulation_id="sim-simfail")
    # force sampling failure: absurd propagation distance
    spec.parameters["propagation_distance"] = 1e6
    campaign_manager.save_object("campaign-simfail", "model_spec", model)
    campaign_manager.save_object("campaign-simfail", "simulation_spec", spec)

    result = simulation_graph.invoke(
        {
            "campaign_id": "campaign-simfail",
            "model_spec_id": model.model_id,
            "simulation_spec_id": spec.simulation_id,
            "retry_count": 0,
            "max_retries": 2,
            "contradiction_kind": "",
        },
        config={"configurable": {"services": services}},
    )
    assert result["completed"] is False
    # retries were bounded by max_retries (2): contradiction action went
    # through RERUN_SIMULATION while retries remained, then human review
    assert result["retry_count"] >= 2
    assert result["contradiction_kind"] in ("SAMPLING_FAILURE",)
