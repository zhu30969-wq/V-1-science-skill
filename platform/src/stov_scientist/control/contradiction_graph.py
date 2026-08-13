"""ContradictionGraph (spec PHASE 11).

Classification of prediction/simulation disagreement with deterministic
routing (spec §45). The graph never revises hypotheses on its own —
revision decisions go through the parent research graph and, where
required, the Human Gate.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from stov_scientist.control.routers import (
    classify_contradiction,
    contradiction_action,
    route_contradiction,
)
from stov_scientist.schemas import ContradictionRecord, ContradictionStatus, ContradictionType


class ContradictionState(TypedDict, total=False):
    contradiction_id: str
    run_status: str
    sampling_ok: bool
    domain_violation: bool
    evidence_contradiction: bool
    prediction_mismatch: bool
    simulation_retries_left: int
    model_revisions_left: int
    kind: str
    route: str
    action: str
    resolution_plan: str


def classify_node(state: ContradictionState) -> dict:
    kind = classify_contradiction(
        run_status=state.get("run_status", ""),
        sampling_ok=state.get("sampling_ok", True),
        domain_violation=state.get("domain_violation", False),
        evidence_contradiction=state.get("evidence_contradiction", False),
        prediction_mismatch=state.get("prediction_mismatch", False),
    )
    return {
        "kind": kind.value,
        "route": route_contradiction(kind),
    }


def route_node(state: ContradictionState) -> dict:
    kind = ContradictionType(state["kind"])
    action = contradiction_action(
        kind,
        simulation_retries_left=state.get("simulation_retries_left", 0),
        model_revisions_left=state.get("model_revisions_left", 0),
    )
    plan = {
        ContradictionType.NUMERICAL_FAILURE: (
            "fix numerical setup (refinement / solver parameters) and rerun"
        ),
        ContradictionType.SAMPLING_FAILURE: "redesign sampling (grid) and rerun",
        ContradictionType.MODEL_DOMAIN_VIOLATION: "revise model/domain and revalidate",
        ContradictionType.EVIDENCE_CONTRADICTION: "evidence review",
        ContradictionType.PHYSICAL_CONTRADICTION: "model/hypothesis review",
        ContradictionType.INDETERMINATE: "additional test or Human Gate",
    }[kind]
    return {"action": action, "resolution_plan": plan}


def classify_and_route(
    *,
    contradiction_id: str,
    run_status: str = "",
    sampling_ok: bool = True,
    domain_violation: bool = False,
    evidence_contradiction: bool = False,
    prediction_mismatch: bool = False,
    simulation_retries_left: int = 0,
    model_revisions_left: int = 0,
) -> tuple[ContradictionRecord, str]:
    """One-shot classification + routing (used by the simulation graph)."""
    kind = classify_contradiction(
        run_status=run_status,
        sampling_ok=sampling_ok,
        domain_violation=domain_violation,
        evidence_contradiction=evidence_contradiction,
        prediction_mismatch=prediction_mismatch,
    )
    action = contradiction_action(
        kind,
        simulation_retries_left=simulation_retries_left,
        model_revisions_left=model_revisions_left,
    )
    record = ContradictionRecord(
        contradiction_id=contradiction_id,
        kind=kind,
        status=ContradictionStatus.ROUTED,
        description=f"classified {kind.value} -> {action}",
        routing_decision=action,
        resolution_plan={
            ContradictionType.NUMERICAL_FAILURE: (
                "fix numerical setup (refinement / solver parameters) and rerun"
            ),
            ContradictionType.SAMPLING_FAILURE: "redesign sampling (grid) and rerun",
            ContradictionType.MODEL_DOMAIN_VIOLATION: "revise model/domain and revalidate",
            ContradictionType.EVIDENCE_CONTRADICTION: "evidence review",
            ContradictionType.PHYSICAL_CONTRADICTION: "model/hypothesis review",
            ContradictionType.INDETERMINATE: "additional test or Human Gate",
        }[kind],
    )
    return record, action


def build_contradiction_graph() -> StateGraph:
    builder = StateGraph(ContradictionState)
    builder.add_node("classify", classify_node)
    builder.add_node("route", route_node)
    builder.add_edge(START, "classify")
    builder.add_edge("classify", "route")
    builder.add_edge("route", END)
    return builder


contradiction_graph = build_contradiction_graph().compile()
