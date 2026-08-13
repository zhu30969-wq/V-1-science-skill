"""ScientificClaim (spec §17).

Forbidden: PROVEN_TRUE. The strongest admissible status is
SUPPORTED_WITHIN_SCOPE.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord


class ClaimStatus(StrEnum):
    UNASSESSED = "UNASSESSED"
    SUPPORTED_WITHIN_SCOPE = "SUPPORTED_WITHIN_SCOPE"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ScientificClaim(BaseRecord):
    claim_id: ID
    statement: str
    scope: str = Field(description="explicit scope boundary of the claim")
    model_id: ID | None = None
    hypothesis_id: ID | None = None
    supporting_evidence_ids: list[ID] = Field(default_factory=list)
    contradicting_evidence_ids: list[ID] = Field(default_factory=list)
    simulation_run_ids: list[ID] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.UNASSESSED

    def evidence_lineage(self) -> dict[str, list[ID]]:
        """Claim -> Evidence -> Model -> Simulation -> Parameters traceability."""
        return {
            "supporting": self.supporting_evidence_ids,
            "contradicting": self.contradicting_evidence_ids,
            "simulation_runs": self.simulation_run_ids,
        }
