"""Hypothesis worker (spec §33): skills hypothesis-generation,
scientific-brainstorming.

Produces HypothesisCandidate[] via structured output. Status vocabulary
comes from HypothesisStatus; PROVEN/TRUE are structurally impossible.

The worker NEVER ranks hypotheses as truth probabilities (spec §11): it may
fill qualitative transparency axes (testability, evidence coverage,
assumption burden, feasibility) for the Human Gate.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from stov_scientist.schemas import (
    EvidenceSet,
    FalsificationCondition,
    HypothesisCandidate,
    HypothesisStatus,
    Prediction,
    ResearchProblem,
)
from stov_scientist.workers.base import WorkerConfig, run_structured

HYPOTHESIS_WORKER_SKILLS = ["hypothesis-generation", "scientific-brainstorming"]


class HypothesisDraft(BaseModel):
    statement: str = Field(description="falsifiable hypothesis statement")
    claim_type: str = Field(description="MECHANISM / BEHAVIOUR / RELATION / PARAMETRIC")
    assumptions: list[str] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    predictions: list[str] = Field(
        default_factory=list, description="observable predictions, 'observable: expected outcome'"
    )
    falsification_conditions: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    testability: str = "UNASSESSED"
    evidence_coverage: str = "UNASSESSED"
    assumption_burden: str = "UNASSESSED"
    experimental_feasibility: str = "UNASSESSED"
    computational_feasibility: str = "UNASSESSED"


class HypothesisDrafts(BaseModel):
    hypotheses: list[HypothesisDraft] = Field(min_length=1)
    rationale: str = ""


def make_hypothesis_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id="hypothesis",
        description="bounded hypothesis + rival generation",
        skills=HYPOTHESIS_WORKER_SKILLS,
        model_kind="main",
    )


def generate_hypotheses(
    model: BaseChatModel,
    problem: ResearchProblem,
    evidence: EvidenceSet | None,
    *,
    n_rivals: int = 2,
) -> list[HypothesisCandidate]:
    """Generate candidate hypotheses (primary + rivals) as structured output.

    Deterministic scaffolding (ids, status CANDIDATE) is applied here; the
    LLM contributes scientific content only. Rival hypotheses are generated
    in the same call and cross-linked via rival_hypothesis_ids afterwards.
    """
    evidence_notes = _evidence_notes(evidence)
    messages = [
        SystemMessage(
            content=(
                "You are a hypothesis-generation worker inside a scientific "
                "control plane. Generate falsifiable hypotheses for the given "
                "research problem, plus rival hypotheses. Rules: LLM output is "
                "not evidence; hypotheses are never TRUE/PROVEN; include "
                "falsification conditions; predictions must name observables; "
                f"generate 1 primary + {n_rivals} rival hypotheses."
            )
        ),
        HumanMessage(
            content=f"Problem: {problem.model_dump_json()}\n"
            f"Evidence notes: {evidence_notes}\n"
            f"Scope: {problem.scope}; excluded: {problem.excluded_scope}"
        ),
    ]
    result = run_structured(model, HypothesisDrafts, messages)
    if not result.ok or result.value is None:
        return []
    drafts: list[HypothesisDraft] = list(result.value.hypotheses)

    candidates: list[HypothesisCandidate] = []
    for i, draft in enumerate(drafts):
        candidates.append(
            HypothesisCandidate(
                hypothesis_id=f"h-{problem.problem_id}-{i + 1}",
                statement=draft.statement,
                claim_type=draft.claim_type,
                status=HypothesisStatus.CANDIDATE,
                assumptions=draft.assumptions,
                boundary_conditions=draft.boundary_conditions,
                predictions=[
                    Prediction(
                        prediction_id=f"p-{problem.problem_id}-{i + 1}-{j + 1}",
                        hypothesis_id=f"h-{problem.problem_id}-{i + 1}",
                        observable=(p.split(":", 1)[0].strip() if ":" in p else p.strip()),
                        expected_outcome=(p.split(":", 1)[1].strip() if ":" in p else ""),
                    )
                    for j, p in enumerate(draft.predictions)
                ],
                falsification_conditions=[
                    FalsificationCondition(
                        condition_id=f"fc-{problem.problem_id}-{i + 1}-{j + 1}",
                        statement=s,
                    )
                    for j, s in enumerate(draft.falsification_conditions)
                ],
                unknowns=draft.unknowns,
                testability=draft.testability,
                evidence_coverage=draft.evidence_coverage,
                assumption_burden=draft.assumption_burden,
                experimental_feasibility=draft.experimental_feasibility,
                computational_feasibility=draft.computational_feasibility,
            )
        )
    # cross-link rivals
    ids = [c.hypothesis_id for c in candidates]
    for c in candidates:
        c.rival_hypothesis_ids = [i for i in ids if i != c.hypothesis_id]
    return candidates


def _evidence_notes(evidence: EvidenceSet | None) -> str:
    if evidence is None:
        return "no evidence retrieved yet"
    lines = []
    for r in evidence.records[:20]:
        lines.append(f"- [{r.relation.value}] {r.title} ({r.year})")
    return "\n".join(lines) or "evidence set is empty"
