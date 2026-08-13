"""ValidationGraph (spec PHASE 10): deterministic validation subgraph.

Runs the ordered validator chain on a ScientificModelSpec; on failure
routes to model revision with the AcceptancePolicy bound
(max_model_revisions); exceeding the bound -> HUMAN_REVIEW_REQUIRED.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from stov_scientist.validators import ValidatorContext, run_validators


class ValidationState(TypedDict, total=False):
    campaign_id: str
    model_spec_id: str
    validation_report_id: str
    model_revision_count: int
    max_model_revisions: int
    validation_passed: bool
    validation_message: str
    action: str  # PASS / REVISE_MODEL / HUMAN_REVIEW_REQUIRED


def validate_model_node(state: ValidationState, config) -> dict:
    services = config["configurable"]["services"]
    campaigns = services.campaigns
    campaign_id = state["campaign_id"]

    from stov_scientist.schemas import ScientificModelSpec, ScientificOntology

    model = campaigns.load_object(
        campaign_id, "model_spec", schema=ScientificModelSpec
    )
    ontology = campaigns.load_object(
        campaign_id, "ontology", schema=ScientificOntology
    )
    if model is None:
        return {
            "validation_passed": False,
            "validation_message": "model spec missing",
            "action": "REVISE_MODEL",
        }

    context = ValidatorContext(
        models={model.model_id: model},
        ontology=ontology,
    )
    report = run_validators(model, context)
    campaigns.save_object(campaign_id, "validation_report", report)

    revision_count = state.get("model_revision_count", 0)
    max_revisions = state.get("max_model_revisions", 3)
    if report.passed:
        return {
            "validation_report_id": report.report_id,
            "validation_passed": True,
            "validation_message": "all mandatory validators passed",
            "action": "PASS",
        }
    if revision_count < max_revisions:
        return {
            "validation_report_id": report.report_id,
            "validation_passed": False,
            "validation_message": (
                f"validation failed at {report.stop_level.value if report.stop_level else '?'}: "
                + "; ".join(r.message for r in report.failed)
            ),
            "action": "REVISE_MODEL",
        }
    return {
        "validation_report_id": report.report_id,
        "validation_passed": False,
        "validation_message": (
            f"validation failed after {revision_count} revisions "
            f"(limit {max_revisions}): HUMAN_REVIEW_REQUIRED"
        ),
        "action": "HUMAN_REVIEW_REQUIRED",
    }


def build_validation_graph() -> StateGraph:
    builder = StateGraph(ValidationState)
    builder.add_node("validate_model", validate_model_node)
    builder.add_edge(START, "validate_model")
    builder.add_edge("validate_model", END)
    return builder


validation_graph = build_validation_graph().compile()
