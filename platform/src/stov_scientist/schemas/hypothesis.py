"""HypothesisCandidate (spec §10).

Forbidden statuses: PROVEN, TRUE. A hypothesis is never assigned an
automatic "truth probability" (spec §11).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord


class HypothesisStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    UNDER_REVIEW = "UNDER_REVIEW"
    SELECTED_FOR_TEST = "SELECTED_FOR_TEST"
    SUPPORTED_WITHIN_SCOPE = "SUPPORTED_WITHIN_SCOPE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONTRADICTED = "CONTRADICTED"


class Prediction(BaseRecord):
    prediction_id: ID
    hypothesis_id: ID
    observable: str
    expected_outcome: str
    conditions: str = ""
    evaluated: bool = False
    evaluation_result: str = Field(
        default="NOT_EVALUATED",
        description="one of NOT_EVALUATED / CONSISTENT / INCONSISTENT / INDETERMINATE",
    )


class FalsificationCondition(BaseRecord):
    condition_id: ID
    statement: str
    test_procedure: str = ""


class HypothesisCandidate(BaseRecord):
    hypothesis_id: ID
    statement: str
    claim_type: str = Field(
        default="UNSPECIFIED",
        description="e.g. MECHANISM / BEHAVIOUR / RELATION / PARAMETRIC",
    )
    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    assumptions: list[str] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    supporting_evidence_ids: list[ID] = Field(default_factory=list)
    contradicting_evidence_ids: list[ID] = Field(default_factory=list)
    rival_hypothesis_ids: list[ID] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    falsification_conditions: list[FalsificationCondition] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    # Transparency axes shown to the human gate — NOT automatic truth scores
    testability: str = Field(
        default="UNASSESSED",
        description="qualitative: UNASSESSED / LOW / MEDIUM / HIGH (testability, not truth)",
    )
    evidence_coverage: str = "UNASSESSED"
    assumption_burden: str = "UNASSESSED"
    experimental_feasibility: str = "UNASSESSED"
    computational_feasibility: str = "UNASSESSED"
    known_contradictions: list[str] = Field(default_factory=list)
