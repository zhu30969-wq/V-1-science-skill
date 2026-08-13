"""ResearchCampaign + AcceptancePolicy + HumanDecision (spec §13, §44, §42).

AcceptancePolicy forbids universal thresholds like ``physics_score >= 0.9``:
convergence tolerances are per-campaign rules.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow
from stov_scientist.schemas.problem import ResearchProblem


class CampaignStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class GateDecision(StrEnum):
    APPROVE = "APPROVE"
    EDIT = "EDIT"
    REJECT = "REJECT"


class ConvergenceRule(BaseRecord):
    rule_id: ID
    metric: str = Field(description="e.g. 'relative_change_of_observable'")
    target: float = Field(description="campaign-defined tolerance, e.g. 1e-3")
    min_refinements: int = 1
    note: str = ""


class AcceptancePolicy(BaseRecord):
    policy_id: ID
    mandatory_validators: list[str] = Field(
        default_factory=lambda: [
            "schema",
            "units",
            "dimensions",
            "symbols",
            "limits",
            "boundary",
            "sampling",
        ]
    )
    required_observables: list[str] = Field(default_factory=list)
    convergence_rules: list[ConvergenceRule] = Field(default_factory=list)
    critical_contradiction_policy: str = Field(
        default="block_final_claim",
        description="how CRITICAL unresolved contradictions gate the final claim",
    )
    max_model_revisions: int = 3
    max_simulation_retries: int = 2
    max_research_iterations: int = 3
    final_human_approval_required: bool = True


class HumanDecision(BaseRecord):
    decision_id: ID
    gate: str = Field(description="SCOPE / HYPOTHESIS_DIRECTION / FINAL_CLAIM")
    object_id: ID
    decision: GateDecision
    rationale: str = ""
    decided_by: str = "human"
    decided_at: datetime = Field(default_factory=utcnow)


class ResearchCampaign(BaseRecord):
    campaign_id: ID
    title: str
    research_problem: ResearchProblem
    acceptance_policy: AcceptancePolicy
    status: CampaignStatus = CampaignStatus.DRAFT
    owner: str = "unknown"
    created_at: datetime = Field(default_factory=utcnow)
    human_decisions: list[HumanDecision] = Field(default_factory=list)
