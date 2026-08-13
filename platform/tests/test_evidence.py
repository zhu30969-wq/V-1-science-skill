"""Evidence ledger + claim transitions + Scientific Judge tests."""

from __future__ import annotations

import pytest

from stov_scientist.errors import EvidenceError
from stov_scientist.evidence.claims import ClaimLedger
from stov_scientist.evidence.judge import JudgeInputs, judge
from stov_scientist.evidence.ledger import EvidenceLedger
from stov_scientist.schemas import (
    AcceptancePolicy,
    ClaimStatus,
    ContradictionRecord,
    ContradictionStatus,
    ContradictionType,
    EvidenceRecord,
    EvidenceRelation,
    JudgementStatus,
    ScientificClaim,
    SearchBoundary,
    ValidationLevel,
    ValidationReport,
    ValidationResult,
)


def make_record(evidence_id: str = "ev-1", relation: str = "SUPPORT") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        source_type="JOURNAL",
        source_id="W1",
        title="Study of spatiotemporal vortices",
        year=2020,
        identifiers={"doi": "10.1000/test"},
        search_boundary_id="b-1",
        relation=EvidenceRelation(relation),
    )


def test_ledger_add_and_list():
    ledger = EvidenceLedger()
    ledger.add_boundary(SearchBoundary(search_boundary_id="b-1", databases=["openalex"]))
    ledger.add_record(make_record("ev-1"), "es-1")
    ledger.add_record(make_record("ev-2", "CONTRADICT"), "es-1")
    assert len(ledger.list_records("es-1")) == 2
    assert len(ledger.list_records("es-1", EvidenceRelation.CONTRADICT)) == 1
    assert ledger.get_record("ev-1").title == "Study of spatiotemporal vortices"
    assert ledger.get_boundary("b-1").databases == ["openalex"]


def test_ledger_jsonl_export(tmp_path):
    ledger = EvidenceLedger()
    ledger.add_record(make_record("ev-1"), "es-1")
    n = ledger.export_jsonl(tmp_path / "evidence.jsonl", "es-1")
    assert n == 1
    assert (tmp_path / "evidence.jsonl").exists()


def test_claim_status_transitions_guarded():
    ledger = ClaimLedger()
    claim = ScientificClaim(claim_id="c-1", statement="x", scope="s", status=ClaimStatus.UNASSESSED)
    ledger.add_claim(claim)
    updated = ledger.update_status("c-1", ClaimStatus.INCONCLUSIVE)
    assert updated.status is ClaimStatus.INCONCLUSIVE
    # INCONCLUSIVE -> PARTIALLY_SUPPORTED allowed
    updated = ledger.update_status("c-1", ClaimStatus.PARTIALLY_SUPPORTED)
    assert updated.status is ClaimStatus.PARTIALLY_SUPPORTED


def test_claim_unknown_id_raises():
    ledger = ClaimLedger()
    with pytest.raises(EvidenceError):
        ledger.update_status("nope", ClaimStatus.INCONCLUSIVE)


def make_validation_report(passed: bool) -> ValidationReport:
    return ValidationReport(
        report_id="vr-1",
        target_id="model-1",
        target_kind="MODEL_SPEC",
        results=[
            ValidationResult(
                check_id="c-1",
                level=ValidationLevel.SCHEMA,
                name="schema",
                passed=passed,
                message="ok" if passed else "bad",
            )
        ],
    )


def test_judge_never_says_proven():
    """The judge vocabulary has no PROVEN status anywhere."""
    for status in JudgementStatus:
        assert "PROVEN" not in status.value


def test_judge_supported_within_scope_path():
    claim = ScientificClaim(claim_id="c-1", statement="s", scope="in scope")
    inputs = JudgeInputs(
        claim=claim,
        policy=AcceptancePolicy(policy_id="p-1"),
        validation_reports=[make_validation_report(True)],
        simulation_converged=True,
        evidence_count=(2, 0),
        provenance_complete=True,
        reproducibility_ok=True,
    )
    judgement = judge(inputs)
    assert judgement.status is JudgementStatus.SUPPORTED_WITHIN_SCOPE


def test_judge_insufficient_evidence_without_anything():
    claim = ScientificClaim(claim_id="c-1", statement="s", scope="s")
    judgement = judge(JudgeInputs(claim=claim))
    assert judgement.status is JudgementStatus.INSUFFICIENT_EVIDENCE


def test_judge_validation_failure_is_inconclusive_not_contradicted():
    """Numerical/validation failure must not become a physical contradiction."""
    claim = ScientificClaim(claim_id="c-1", statement="s", scope="s")
    inputs = JudgeInputs(
        claim=claim,
        policy=AcceptancePolicy(policy_id="p-1"),
        validation_reports=[make_validation_report(False)],
        simulation_converged=True,
        evidence_count=(3, 1),
        provenance_complete=True,
    )
    judgement = judge(inputs)
    assert judgement.status is JudgementStatus.INCONCLUSIVE


def test_judge_critical_unresolved_contradiction_blocks():
    claim = ScientificClaim(claim_id="c-1", statement="s", scope="s")
    contradiction = ContradictionRecord(
        contradiction_id="cx-1",
        kind=ContradictionType.PHYSICAL_CONTRADICTION,
        severity="CRITICAL",
        status=ContradictionStatus.OPEN,
        description="unresolved",
    )
    inputs = JudgeInputs(
        claim=claim,
        policy=AcceptancePolicy(policy_id="p-1", critical_contradiction_policy="block_final_claim"),
        validation_reports=[make_validation_report(True)],
        simulation_converged=True,
        evidence_count=(2, 0),
        contradictions=[contradiction],
    )
    judgement = judge(inputs)
    assert judgement.status is JudgementStatus.CONTRADICTED


def test_judge_inconclusive_when_not_converged():
    claim = ScientificClaim(claim_id="c-1", statement="s", scope="s")
    inputs = JudgeInputs(
        claim=claim,
        policy=AcceptancePolicy(policy_id="p-1"),
        validation_reports=[make_validation_report(True)],
        simulation_converged=False,
        evidence_count=(2, 0),
    )
    judgement = judge(inputs)
    assert judgement.status is JudgementStatus.INCONCLUSIVE
