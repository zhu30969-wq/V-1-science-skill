"""Synthesis worker (spec §32): drafts the scientific claim bundle from
validated content. The Scientific Judge — not this worker — assigns the
final status. The worker's drafts start at UNASSESSED.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from stov_scientist.schemas import (
    ClaimStatus,
    ScientificClaim,
    ScientificJudgement,
    ScientificModelSpec,
    SimulationRun,
)
from stov_scientist.workers.base import WorkerConfig, run_structured


class ClaimDraft(BaseModel):
    statement: str = Field(description="single falsifiable claim statement with explicit scope")
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ClaimDrafts(BaseModel):
    claims: list[ClaimDraft] = Field(default_factory=list)


def make_synthesis_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id="synthesis",
        description="drafts claim bundles from validated evidence (judge assigns status)",
        skills=["scientific-brainstorming"],
        model_kind="main",
    )


def synthesize_claims(
    model: BaseChatModel,
    *,
    campaign_id: str,
    model_spec: ScientificModelSpec | None,
    simulation_runs: list[SimulationRun],
    judgements: list[ScientificJudgement],
    evidence_ids_supporting: list[str],
    evidence_ids_contradicting: list[str],
) -> list[ScientificClaim]:
    """Draft claims; status comes from the Scientific Judge afterwards."""
    context = {
        "model": model_spec.model_id if model_spec else None,
        "simulation_runs": [
            {"run_id": r.run_id, "status": r.status.value, "converged": (r.convergence_result.achieved if r.convergence_result else None)}
            for r in simulation_runs
        ],
        "judgements": [j.status.value for j in judgements],
        "evidence": {
            "supporting": len(evidence_ids_supporting),
            "contradicting": len(evidence_ids_contradicting),
        },
    }
    messages = [
        SystemMessage(
            content=(
                "You draft scientific claims from validated research content. "
                "Rules: every claim states its scope; statuses are assigned "
                "by the Scientific Judge, never by you; a claim is never "
                "PROVEN or TRUE; numerical failures are never physical "
                "contradictions; INCONCLUSIVE is a valid outcome; include "
                "assumptions and limitations."
            )
        ),
        HumanMessage(content=f"Research content: {context}"),
    ]
    result = run_structured(model, ClaimDrafts, messages)
    if not result.ok or result.value is None:
        return []
    out = []
    for i, draft in enumerate(result.value.claims):
        out.append(
            ScientificClaim(
                claim_id=f"claim-{campaign_id}-{i + 1}",
                statement=draft.statement,
                scope=model_spec.validity_domain.description if model_spec else "",
                model_id=model_spec.model_id if model_spec else None,
                supporting_evidence_ids=evidence_ids_supporting,
                contradicting_evidence_ids=evidence_ids_contradicting,
                simulation_run_ids=[r.run_id for r in simulation_runs],
                assumptions=draft.assumptions,
                limitations=draft.limitations,
                status=ClaimStatus.UNASSESSED,
            )
        )
    return out
