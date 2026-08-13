"""Routers: model route selector (spec §40), contradiction classifier and
routing table (spec §45). Pure functions — fully unit-testable, no LLM."""

from __future__ import annotations

from stov_scientist.schemas import ContradictionType, ResearchProblem

NOT_IMPLEMENTED_ROUTES = ("DATA_DRIVEN", "HYBRID")

CONTRADICTION_ROUTES: dict[ContradictionType, str] = {
    ContradictionType.NUMERICAL_FAILURE: "fix_numerical_setup",
    ContradictionType.SAMPLING_FAILURE: "redesign_sampling",
    ContradictionType.MODEL_DOMAIN_VIOLATION: "revise_model_domain",
    ContradictionType.EVIDENCE_CONTRADICTION: "evidence_review",
    ContradictionType.PHYSICAL_CONTRADICTION: "model_hypothesis_review",
    ContradictionType.INDETERMINATE: "additional_test_or_human",
}


def select_model_route(
    problem: ResearchProblem,
    *,
    requested: str | None = None,
) -> tuple[str, list[str]]:
    """Choose ANALYTICAL / NUMERICAL / DATA_DRIVEN / HYBRID.

    DATA_DRIVEN and HYBRID have no reliable implementation in v1 (spec §40):
    they are flagged NOT_IMPLEMENTED and the pipeline is routed to the
    implemented subset — never silently faked.
    """
    warnings: list[str] = []
    route = requested or ("NUMERICAL" if problem.kind != "THEORY" else "ANALYTICAL")
    if route in NOT_IMPLEMENTED_ROUTES:
        warnings.append(
            f"model route {route} is NOT_IMPLEMENTED in v1; routing to "
            f"the implemented subset (ANALYTICAL/NUMERICAL) instead"
        )
        route = "NUMERICAL" if problem.kind != "THEORY" else "ANALYTICAL"
    return route, warnings


def classify_contradiction(
    *,
    run_status: str = "",
    sampling_ok: bool = True,
    domain_violation: bool = False,
    evidence_contradiction: bool = False,
    prediction_mismatch: bool = False,
) -> ContradictionType:
    """Classify a prediction/simulation disagreement (spec PHASE 11).

    Numerical and sampling failures are classified BEFORE any physical
    interpretation — a numerical failure is never a physical contradiction.
    """
    if run_status == "SAMPLING_FAILURE" or not sampling_ok:
        return ContradictionType.SAMPLING_FAILURE
    if run_status == "NUMERICAL_FAILURE":
        return ContradictionType.NUMERICAL_FAILURE
    if run_status == "RESOURCE_LIMIT":
        return ContradictionType.INDETERMINATE
    if domain_violation:
        return ContradictionType.MODEL_DOMAIN_VIOLATION
    if evidence_contradiction:
        return ContradictionType.EVIDENCE_CONTRADICTION
    if prediction_mismatch:
        return ContradictionType.PHYSICAL_CONTRADICTION
    return ContradictionType.INDETERMINATE


def route_contradiction(kind: ContradictionType) -> str:
    """The §45 routing table."""
    return CONTRADICTION_ROUTES[kind]


def contradiction_action(
    kind: ContradictionType,
    *,
    simulation_retries_left: int,
    model_revisions_left: int,
) -> str:
    """Routing decision with loop-limit awareness (spec §43, §45).

    Returns: RERUN_SIMULATION / REVISE_MODEL / EVIDENCE_REVIEW /
    ADDITIONAL_TEST_OR_HUMAN / HUMAN_REVIEW_REQUIRED
    """
    route = route_contradiction(kind)
    if route in ("fix_numerical_setup", "redesign_sampling"):
        return "RERUN_SIMULATION" if simulation_retries_left > 0 else "HUMAN_REVIEW_REQUIRED"
    if route == "revise_model_domain":
        return "REVISE_MODEL" if model_revisions_left > 0 else "HUMAN_REVIEW_REQUIRED"
    if route == "evidence_review":
        return "EVIDENCE_REVIEW"
    if route == "model_hypothesis_review":
        return "REVISE_MODEL" if model_revisions_left > 0 else "HUMAN_REVIEW_REQUIRED"
    return "ADDITIONAL_TEST_OR_HUMAN"
