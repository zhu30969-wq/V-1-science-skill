"""Evidence ledger + claims + judge + provenance (spec §18, PHASE 12)."""

from stov_scientist.evidence.claims import ClaimLedger
from stov_scientist.evidence.judge import JudgeInputs, judge
from stov_scientist.evidence.ledger import EvidenceLedger, merge_evidence_sets
from stov_scientist.evidence.provenance import (
    capture_environment,
    claim_provenance_complete,
    evidence_provenance_complete,
)

__all__ = [
    "ClaimLedger",
    "EvidenceLedger",
    "JudgeInputs",
    "capture_environment",
    "claim_provenance_complete",
    "evidence_provenance_complete",
    "judge",
    "merge_evidence_sets",
]
