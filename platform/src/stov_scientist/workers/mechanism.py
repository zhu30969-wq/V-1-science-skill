"""Mechanism worker (spec §33): skills sympy, scientific-brainstorming,
stov-optical-conventions, stov-field-modeling, stov-wave-propagation.

Produces MechanismCandidate[] bound to a hypothesis. Physical content is
LLM-drafted; model_requirements and governing principles are checked
against the skill libraries by the control plane (the worker never
bypasses validation).
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from stov_scientist.schemas import (
    HypothesisCandidate,
    MechanismCandidate,
    MechanisticLink,
    PhysicalProcess,
)
from stov_scientist.workers.base import WorkerConfig, run_structured

MECHANISM_WORKER_SKILLS = [
    "sympy",
    "scientific-brainstorming",
    "stov-optical-conventions",
    "stov-field-modeling",
    "stov-wave-propagation",
]


class MechanismDraft(BaseModel):
    description: str
    governing_principles: list[str] = Field(default_factory=list)
    physical_processes: list[str] = Field(default_factory=list)
    mechanistic_links: list[str] = Field(default_factory=list, description="'step A -> step B: description'")
    assumptions: list[str] = Field(default_factory=list)
    boundary_conditions: list[str] = Field(default_factory=list)
    predicted_observables: list[str] = Field(default_factory=list)
    model_requirements: list[str] = Field(default_factory=list)


class MechanismDrafts(BaseModel):
    mechanisms: list[MechanismDraft] = Field(min_length=1)
    alternative_notes: str = ""


def make_mechanism_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id="mechanism",
        description="bounded mechanism exploration for a selected hypothesis",
        skills=MECHANISM_WORKER_SKILLS,
        model_kind="main",
    )


def generate_mechanisms(
    model: BaseChatModel,
    hypothesis: HypothesisCandidate,
) -> list[MechanismCandidate]:
    messages = [
        SystemMessage(
            content=(
                "You are a mechanism-exploration worker. Propose candidate "
                "physical mechanisms for the given hypothesis. Rules: a "
                "mechanism is not evidence; cite governing principles by "
                "name (never fabricate citations); list model requirements; "
                "stay within the hypothesis boundary conditions; state "
                "assumptions explicitly. Use STOV conventions: transverse "
                "plane (x, t), propagation +z, harmonic exp(-i omega t)."
            )
        ),
        HumanMessage(
            content=f"Hypothesis: {hypothesis.model_dump_json()}"
        ),
    ]
    result = run_structured(model, MechanismDrafts, messages)
    if not result.ok or result.value is None:
        return []
    out: list[MechanismCandidate] = []
    for i, draft in enumerate(result.value.mechanisms):
        processes = [
            PhysicalProcess(
                process_id=f"proc-{hypothesis.hypothesis_id}-{i + 1}-{j + 1}",
                name=p,
                description="",
            )
            for j, p in enumerate(draft.physical_processes)
        ]
        links: list[MechanisticLink] = []
        for j, link_text in enumerate(draft.mechanistic_links):
            if "->" in link_text:
                left, right = link_text.split("->", 1)
                from_step = _process_id(processes, left.strip())
                to_step = _process_id(processes, right.split(":", 1)[0].strip())
                links.append(
                    MechanisticLink(
                        link_id=f"link-{hypothesis.hypothesis_id}-{i + 1}-{j + 1}",
                        from_step=from_step,
                        to_step=to_step,
                        description=right.split(":", 1)[1].strip() if ":" in right else link_text,
                    )
                )
        out.append(
            MechanismCandidate(
                mechanism_id=f"mech-{hypothesis.hypothesis_id}-{i + 1}",
                hypothesis_id=hypothesis.hypothesis_id,
                description=draft.description,
                physical_processes=processes,
                mechanistic_links=links,
                governing_principles=draft.governing_principles,
                assumptions=draft.assumptions,
                boundary_conditions=draft.boundary_conditions,
                predicted_observables=draft.predicted_observables,
                evidence_ids=list(hypothesis.supporting_evidence_ids),
                model_requirements=draft.model_requirements,
            )
        )
    # cross-link alternatives
    ids = [m.mechanism_id for m in out]
    for m in out:
        m.alternative_mechanisms = [i for i in ids if i != m.mechanism_id]
    return out


def _process_id(processes: list[PhysicalProcess], name: str) -> str:
    for p in processes:
        if p.name.strip() == name:
            return p.process_id
    return name
