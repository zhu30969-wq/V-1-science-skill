"""ScientificJudgement (spec PHASE 12).

The Scientific Judge reviews evidence completeness, physical validation,
numerical validity, provenance, unresolved contradictions, scope compliance
and reproducibility. It never proposes hypotheses, edits models or runs
simulations. Forbidden output: PROVEN_TRUE.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class JudgementStatus(StrEnum):
    SUPPORTED_WITHIN_SCOPE = "SUPPORTED_WITHIN_SCOPE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ScientificJudgement(BaseRecord):
    judgement_id: ID
    claim_id: ID
    status: JudgementStatus
    evidence_completeness: str = "UNASSESSED"
    physical_validation: str = "UNASSESSED"
    numerical_validity: str = "UNASSESSED"
    provenance_completeness: str = "UNASSESSED"
    unresolved_contradictions: list[ID] = Field(default_factory=list)
    scope_compliance: str = "UNASSESSED"
    reproducibility_status: str = "UNASSESSED"
    rationale: str = ""
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    judged_by: str = "scientific-judge"
