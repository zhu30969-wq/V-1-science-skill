"""Contradiction system (spec PHASE 11, §45).

Classification of prediction/simulation disagreement — routing decides the
response. Numerical failure is NEVER a physical contradiction.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class ContradictionType(StrEnum):
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"
    SAMPLING_FAILURE = "SAMPLING_FAILURE"
    MODEL_DOMAIN_VIOLATION = "MODEL_DOMAIN_VIOLATION"
    EVIDENCE_CONTRADICTION = "EVIDENCE_CONTRADICTION"
    PHYSICAL_CONTRADICTION = "PHYSICAL_CONTRADICTION"
    INDETERMINATE = "INDETERMINATE"


class ContradictionStatus(StrEnum):
    OPEN = "OPEN"
    ROUTED = "ROUTED"
    RESOLVED = "RESOLVED"
    ACKNOWLEDGED_UNRESOLVED = "ACKNOWLEDGED_UNRESOLVED"
    ESCALATED_HUMAN = "ESCALATED_HUMAN"


class ContradictionRecord(BaseRecord):
    contradiction_id: ID
    hypothesis_id: ID | None = None
    model_id: ID | None = None
    prediction_id: ID | None = None
    simulation_run_id: ID | None = None
    kind: ContradictionType
    description: str
    observed: str = ""
    expected: str = ""
    severity: str = Field(default="INFO", description="INFO / WARNING / CRITICAL")
    status: ContradictionStatus = ContradictionStatus.OPEN
    routing_decision: str = ""
    resolution_plan: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


class CounterexampleCandidate(BaseRecord):
    """Output of the counterexample worker (spec §46)."""

    counterexample_id: ID
    target_model_id: ID | None = None
    target_hypothesis_id: ID | None = None
    search_kind: str = Field(
        description="BOUNDARY_CASE / PARAMETER_EXTREME / RIVAL_MECHANISM / "
        "ALTERNATIVE_ASSUMPTION / LITERATURE_CONTRADICTION / NUMERICAL_STRESS"
    )
    description: str
    parameter_set: dict[str, float] = Field(default_factory=dict)
    within_validity_domain: bool = True
    falsifies: bool = False
    status: str = Field(default="CANDIDATE", description="CANDIDATE / TESTED / REJECTED")
    evidence_ids: list[ID] = Field(default_factory=list)
