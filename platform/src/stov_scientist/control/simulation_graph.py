"""SimulationGraph (spec PHASE 10): simulation subgraph with bounded retries.

Retry semantics (spec §45): NUMERICAL_FAILURE -> refine numerical setup
and rerun; SAMPLING_FAILURE -> redesign sampling and rerun. Retries are
bounded by AcceptancePolicy.max_simulation_retries; exceeding the bound ->
HUMAN_REVIEW_REQUIRED. Failures are recorded as ContradictionRecords —
never as physical contradictions.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from stov_scientist.control.contradiction_graph import classify_and_route
from stov_scientist.errors import NoValidSolverError, SimulationError, ValidationError


class SimulationGraphState(TypedDict, total=False):
    campaign_id: str
    model_spec_id: str
    simulation_spec_id: str
    simulation_run_id: str
    run_status: str
    retry_count: int
    max_retries: int
    contradiction_id: str | None
    contradiction_kind: str
    contradiction_action: str
    message: str
    completed: bool


def run_simulation_node(state: SimulationGraphState, config) -> dict:
    services = config["configurable"]["services"]
    campaigns = services.campaigns
    campaign_id = state["campaign_id"]

    from stov_scientist.schemas import (
        ScientificModelSpec,
        SimulationSpec,
    )

    model = campaigns.load_object(
        campaign_id, "model_spec", schema=ScientificModelSpec
    )
    spec = campaigns.load_object(
        campaign_id, "simulation_spec", schema=SimulationSpec
    )
    if model is None or spec is None:
        return {
            "run_status": "NUMERICAL_FAILURE",
            "message": "model or simulation spec missing",
            "completed": False,
        }

    retry_count = state.get("retry_count", 0)
    if retry_count > 0:
        spec = _refine_for_retry(spec, retry_count, state.get("contradiction_kind", ""))

    policy = None
    campaign = campaigns.load_campaign(campaign_id)
    if campaign is not None:
        policy = campaign.acceptance_policy

    try:
        outcome = services.simulation.run(
            model, spec, policy=policy, campaign_id=campaign_id
        )
    except (ValidationError, NoValidSolverError) as exc:
        return {
            "run_status": "DOMAIN_VIOLATION",
            "message": str(exc),
            "completed": False,
        }
    except SimulationError as exc:
        return {
            "run_status": "NUMERICAL_FAILURE",
            "message": str(exc),
            "completed": False,
        }

    campaigns.save_object(campaign_id, "simulation_spec", spec)
    campaigns.save_object(campaign_id, "simulation_run", outcome.run)
    campaigns.save_object(
        campaign_id,
        "observables",
        outcome.observables.as_dict() if outcome.observables else {},
    )
    return {
        "simulation_run_id": outcome.run.run_id,
        "run_status": outcome.run.status.value,
        "message": "; ".join(outcome.run.errors) or "simulation executed",
        "completed": outcome.run.status.value == "COMPLETED",
    }


def classify_simulation_node(state: SimulationGraphState) -> dict:
    status = state.get("run_status", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    sampling_ok = status != "SAMPLING_FAILURE"
    domain_violation = status == "DOMAIN_VIOLATION"

    record, action = classify_and_route(
        contradiction_id=f"contra-{state.get('simulation_spec_id', 'sim')}-{retry_count}",
        run_status=status,
        sampling_ok=sampling_ok,
        domain_violation=domain_violation,
        simulation_retries_left=max_retries - retry_count,
    )
    return {
        "contradiction_id": record.contradiction_id,
        "contradiction_kind": record.kind.value,
        "contradiction_action": action,
    }


def decide_next(state: SimulationGraphState) -> str:
    if state.get("completed"):
        return "done"
    action = state.get("contradiction_action", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if action in ("RERUN_SIMULATION",) and retry_count < max_retries:
        return "rerun"
    return "human_review"


def _refine_for_retry(spec, retry_count: int, kind: str):
    """Deterministic retry refinement: double the transverse grid."""
    updated = spec.model_copy(deep=True)
    if kind == "SAMPLING_FAILURE":
        factor = 2 * (retry_count + 1)
        updated.grid.shape = [n * factor for n in spec.grid.shape]
        updated.grid.spacing = {a: sp / factor for a, sp in spec.grid.spacing.items()}
    else:  # NUMERICAL_FAILURE
        factor = 2**retry_count
        updated.grid.shape = [n * factor for n in spec.grid.shape]
        updated.grid.spacing = {a: sp / factor for a, sp in spec.grid.spacing.items()}
    return updated


def prepare_retry_node(state: SimulationGraphState) -> dict:
    return {"retry_count": state.get("retry_count", 0) + 1}


def build_simulation_graph() -> StateGraph:
    builder = StateGraph(SimulationGraphState)
    builder.add_node("run_simulation", run_simulation_node)
    builder.add_node("classify_simulation", classify_simulation_node)
    builder.add_node("prepare_retry", prepare_retry_node)
    builder.add_edge(START, "run_simulation")
    builder.add_conditional_edges(
        "run_simulation",
        lambda state: "classify" if not state.get("completed") else "done",
        {"classify": "classify_simulation", "done": END},
    )
    builder.add_conditional_edges(
        "classify_simulation",
        decide_next,
        {"rerun": "prepare_retry", "done": END, "human_review": END},
    )
    builder.add_edge("prepare_retry", "run_simulation")
    return builder


simulation_graph = build_simulation_graph().compile()
