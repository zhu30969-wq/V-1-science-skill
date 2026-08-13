"""Literature worker (spec §33): skills literature-review, research-lookup,
citation-management. Bounded: search is deterministic; the LLM only
classifies claim relations (SUPPORT / CONTRADICT / CONTEXT) when asked.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from stov_scientist.literature.search import search_literature
from stov_scientist.schemas import (
    EvidenceRecord,
    EvidenceRelation,
    EvidenceSet,
    ResearchProblem,
)
from stov_scientist.workers.base import WorkerConfig, run_structured

LITERATURE_WORKER_SKILLS = ["literature-review", "research-lookup", "citation-management"]


class RelationAssignments(BaseModel):
    """LLM output contract: per-evidence relation classification."""

    assignments: list[dict[str, str]] = Field(
        description="[{evidence_id, relation}] relation in SUPPORT/CONTRADICT/CONTEXT/UNKNOWN"
    )
    rationale: str = ""


def make_literature_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id="literature",
        description="bounded literature research + evidence relation classification",
        skills=LITERATURE_WORKER_SKILLS,
        tools=[],
        model_kind="fast",
    )


def run_literature_search(
    problem: ResearchProblem,
    *,
    campaign_id: str,
    evidence_set_id: str,
    boundary_id: str,
    queries: list[str] | None = None,
    databases: list[str] | None = None,
    max_per_query: int = 10,
    clients: dict[str, object] | None = None,
) -> EvidenceSet | None:
    """Deterministic multi-database search inside a SearchBoundary.

    Returns None on zero retrieved records (with the boundary recording
    why) — callers must treat this as 'not located within the documented
    search boundary', never 'no literature exists'.
    """
    db = databases or ["openalex", "crossref", "arxiv"]
    qs = queries or [problem.research_question]
    outcome = search_literature(
        qs,
        db,
        campaign_id=campaign_id,
        evidence_set_id=evidence_set_id,
        boundary_id=boundary_id,
        max_per_query=max_per_query,
        clients=clients,
    )
    return outcome.evidence_set


def classify_relations(
    model: BaseChatModel,
    problem: ResearchProblem,
    evidence: EvidenceSet,
) -> list[EvidenceRecord]:
    """LLM-assisted relation classification (deterministic default: CONTEXT).

    The LLM never fabricates records; it only annotates existing ones.
    """
    if not evidence.records:
        return []
    bound_records = [
        {
            "evidence_id": r.evidence_id,
            "title": r.title[:300],
            "summary": r.summary[:800],
        }
        for r in evidence.records
    ]
    messages = [
        SystemMessage(
            content=(
                "You annotate EXISTING literature records for a research problem. "
                "Classify each record's relation to the research question as "
                "SUPPORT / CONTRADICT / CONTEXT / UNKNOWN. Never invent records, "
                "never assign truth probabilities, never claim a search found "
                "'everything'. If unsure: CONTEXT."
            )
        ),
        HumanMessage(
            content=f"Research question: {problem.research_question}\n"
            f"Records: {bound_records}"
        ),
    ]
    result = run_structured(model, RelationAssignments, messages)
    if not result.ok or result.value is None:
        return list(evidence.records)
    assignments = {a["evidence_id"]: a["relation"] for a in result.value.assignments}
    updated = []
    for record in evidence.records:
        relation = assignments.get(record.evidence_id, "CONTEXT")
        try:
            record = record.model_copy(update={"relation": EvidenceRelation(relation)})
        except ValueError:
            record = record.model_copy(update={"relation": EvidenceRelation.CONTEXT})
        updated.append(record)
    return updated
