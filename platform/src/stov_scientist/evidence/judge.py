"""Scientific Judge (spec PHASE 12).

The judge reviews only: evidence completeness, physical validation,
numerical validity, provenance completeness, unresolved contradictions,
scope compliance, reproducibility status.

It never proposes hypotheses, never edits models, never runs simulations.
Its verdicts are deterministic (code evaluator, spec §72) — LLM-as-judge is
not the primary scientific correctness evaluator. Verdict vocabulary comes
from JudgementStatus; PROVEN_TRUE does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stov_scientist.schemas import (
    AcceptancePolicy,
    ClaimStatus,
    ContradictionRecord,
    ContradictionStatus,
    JudgementStatus,
    ScientificClaim,
    ScientificJudgement,
    ValidationReport,
)


@dataclass
class JudgeInputs:
    """Everything the judge is allowed to look at."""

    claim: ScientificClaim
    policy: AcceptancePolicy | None = None
    validation_reports: list[ValidationReport] = field(default_factory=list)
    contradictions: list[ContradictionRecord] = field(default_factory=list)
    simulation_converged: bool | None = None
    evidence_count: tuple[int, int] = (0, 0)  # (supporting, contradicting)
    provenance_complete: bool = False
    reproducibility_ok: bool = False


def _critical(contradictions: list[ContradictionRecord]) -> list[ContradictionRecord]:
    return [
        c
        for c in contradictions
        if c.severity == "CRITICAL"
        and c.status in (ContradictionStatus.OPEN, ContradictionStatus.ROUTED)
    ]


def _unresolved(contradictions: list[ContradictionRecord]) -> list[ContradictionRecord]:
    return [
        c
        for c in contradictions
        if c.status
        in (
            ContradictionStatus.OPEN,
            ContradictionStatus.ROUTED,
            ContradictionStatus.ACKNOWLEDGED_UNRESOLVED,
        )
    ]


def judge(inputs: JudgeInputs) -> ScientificJudgement:
    claim = inputs.claim
    supporting, contradicting = inputs.evidence_count
    critical = _critical(inputs.contradictions)
    unresolved = _unresolved(inputs.contradictions)
    critical_policy = (inputs.policy.critical_contradiction_policy if inputs.policy else None) or (
        "block_final_claim"
    )

    # --- rubric dimensions -------------------------------------------------
    if supporting == 0 and contradicting == 0:
        evidence_completeness = "NONE"
    elif supporting > 0 and contradicting == 0:
        evidence_completeness = "ONE_SIDED"
    elif supporting == 0 and contradicting > 0:
        evidence_completeness = "ONLY_CONTRADICTING"
    else:
        evidence_completeness = "TWO_SIDED"

    reports_ok = bool(inputs.validation_reports) and all(
        r.passed for r in inputs.validation_reports
    )
    physical_validation = (
        "PASSED" if reports_ok else ("FAILED" if inputs.validation_reports else "NOT_RUN")
    )
    numerical_validity = (
        "CONVERGED"
        if inputs.simulation_converged is True
        else ("NOT_CONVERGED" if inputs.simulation_converged is False else "NOT_RUN")
    )
    provenance_completeness = "COMPLETE" if inputs.provenance_complete else "INCOMPLETE"
    reproducibility_status = "REPRODUCIBLE" if inputs.reproducibility_ok else "NOT_ESTABLISHED"
    scope_compliance = "IN_SCOPE" if claim.scope else "UNSPECIFIED"

    # --- verdict ------------------------------------------------------------
    # Critical unresolved contradictions block the final claim when the policy
    # says so (default) — surfaced as CONTRADICTED, never silently dropped.
    if (critical and critical_policy == "block_final_claim") or claim.status is ClaimStatus.CONTRADICTED:
        status = JudgementStatus.CONTRADICTED
    elif evidence_completeness == "NONE" and numerical_validity in ("NOT_RUN",):
        status = JudgementStatus.INSUFFICIENT_EVIDENCE
    elif physical_validation == "FAILED":
        # numerical/validation failure is NOT a scientific contradiction:
        # the claim is simply not established
        status = JudgementStatus.INCONCLUSIVE
    elif not unresolved and reports_ok and numerical_validity == "CONVERGED":
        if evidence_completeness in ("TWO_SIDED", "ONE_SIDED"):
            status = JudgementStatus.SUPPORTED_WITHIN_SCOPE
        else:
            status = JudgementStatus.INSUFFICIENT_EVIDENCE
    elif unresolved or numerical_validity == "NOT_CONVERGED":
        status = JudgementStatus.INCONCLUSIVE
    else:
        status = JudgementStatus.PARTIALLY_SUPPORTED

    rationale_lines = [
        f"evidence: {evidence_completeness} ({supporting} supporting, {contradicting} contradicting)",
        f"physical validation: {physical_validation}",
        f"numerical validity: {numerical_validity}",
        f"provenance: {provenance_completeness}",
        f"unresolved contradictions: {len(unresolved)} (critical: {len(critical)})",
        f"scope: {scope_compliance}",
        f"reproducibility: {reproducibility_status}",
    ]
    return ScientificJudgement(
        judgement_id=f"judge-{claim.claim_id}",
        claim_id=claim.claim_id,
        status=status,
        evidence_completeness=evidence_completeness,
        physical_validation=physical_validation,
        numerical_validity=numerical_validity,
        provenance_completeness=provenance_completeness,
        unresolved_contradictions=[c.contradiction_id for c in unresolved],
        scope_compliance=scope_compliance,
        reproducibility_status=reproducibility_status,
        rationale="; ".join(rationale_lines),
    )
