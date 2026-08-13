"""Counterexample worker (spec §33, §46): skills stov-model-validation,
stov-topology-analysis, stov-numerical-convergence.

Inputs: HypothesisCandidate, ScientificModelSpec, validity_domain,
SimulationSpec. Outputs: CounterexampleCandidate[].

Two modes:
  * deterministic boundary sampling (no LLM): grid over validity-domain
    extremes — runs offline, used by unit tests and benchmarks.
  * LLM exploration (long-horizon): rival mechanisms, alternative
    assumptions, literature contradiction angles.
"""

from __future__ import annotations

import numpy as np
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from stov_scientist.schemas import (
    CounterexampleCandidate,
    HypothesisCandidate,
    ScientificModelSpec,
    SimulationSpec,
)
from stov_scientist.workers.base import WorkerConfig, run_structured

COUNTEREXAMPLE_WORKER_SKILLS = [
    "stov-model-validation",
    "stov-topology-analysis",
    "stov-numerical-convergence",
]


class CounterexampleDraft(BaseModel):
    search_kind: str = Field(description="BOUNDARY_CASE/PARAMETER_EXTREME/RIVAL_MECHANISM/ALTERNATIVE_ASSUMPTION/LITERATURE_CONTRADICTION/NUMERICAL_STRESS")
    description: str
    parameter_set: dict[str, float] = Field(default_factory=dict)
    within_validity_domain: bool = True
    rationale: str = ""


class CounterexampleDrafts(BaseModel):
    counterexamples: list[CounterexampleDraft] = Field(default_factory=list)
    notes: str = ""


def make_counterexample_worker_config() -> WorkerConfig:
    return WorkerConfig(
        worker_id="counterexample",
        description="bounded counterexample exploration (boundary cases, parameter extremes, stress tests)",
        skills=COUNTEREXAMPLE_WORKER_SKILLS,
        model_kind="main",
    )


def boundary_cases(
    model: ScientificModelSpec,
    *,
    n_points_per_axis: int = 3,
    seed: int = 0,
) -> list[CounterexampleCandidate]:
    """Deterministic boundary-case sampling over the validity domain.

    For each bounded parameter: {min, midpoint, max}. Produces cartesian
    corners up to a cap. No LLM involved.
    """
    ranges = model.validity_domain.parameter_ranges
    bounded = {s: (lo, hi) for s, (lo, hi) in ranges.items() if lo is not None and hi is not None}
    if not bounded:
        return []
    axes = [
        [lo, (lo + hi) / 2, hi][:n_points_per_axis] for lo, hi in bounded.values()
    ]
    candidates: list[CounterexampleCandidate] = []
    for i, combo in enumerate(np.array(np.meshgrid(*axes, indexing="ij")).reshape(len(bounded), -1).T):
        if len(candidates) >= 16:
            break
        params = {name: float(v) for name, v in zip(bounded, combo, strict=True)}
        candidates.append(
            CounterexampleCandidate(
                counterexample_id=f"cx-{model.model_id}-boundary-{i + 1}",
                target_model_id=model.model_id,
                search_kind="BOUNDARY_CASE",
                description=f"boundary case {params} (deterministic sampling)",
                parameter_set=params,
                within_validity_domain=True,
            )
        )
    return candidates


def numerical_stress_cases(
    spec: SimulationSpec,
    *,
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
) -> list[CounterexampleCandidate]:
    """Numerical stress: same physics, different random seeds — the observable
    must be seed-stable. Deterministic candidate generation (no LLM)."""
    return [
        CounterexampleCandidate(
            counterexample_id=f"cx-{spec.simulation_id}-stress-{s}",
            target_model_id=spec.model_id,
            search_kind="NUMERICAL_STRESS",
            description=f"ensemble seed {s}: observable stability stress test",
            parameter_set={"random_seed": float(s)},
            within_validity_domain=True,
        )
        for s in seeds
    ]


def explore_counterexamples(
    model: BaseChatModel,
    hypothesis: HypothesisCandidate,
    model_spec: ScientificModelSpec,
) -> list[CounterexampleCandidate]:
    """LLM long-horizon exploration: rival mechanisms, alternative
    assumptions, literature contradiction angles (bounded worker)."""
    messages = [
        SystemMessage(
            content=(
                "You are a counterexample worker for a scientific model. "
                "Search for: boundary cases, parameter extremes, rival "
                "mechanisms, alternative assumptions, literature "
                "contradictions, numerical stress angles. Rules: a proposed "
                "counterexample is NOT a falsification until TESTED; stay "
                "within the declared validity domain unless explicitly "
                "flagged otherwise; never fabricate literature; return "
                "structured output only."
            )
        ),
        HumanMessage(
            content=(
                f"Hypothesis: {hypothesis.model_dump_json()}\n"
                f"Model: {model_spec.model_dump_json()}"
            )
        ),
    ]
    result = run_structured(model, CounterexampleDrafts, messages)
    if not result.ok or result.value is None:
        return []
    out = []
    for i, draft in enumerate(result.value.counterexamples):
        out.append(
            CounterexampleCandidate(
                counterexample_id=f"cx-{model_spec.model_id}-llm-{i + 1}",
                target_model_id=model_spec.model_id,
                target_hypothesis_id=hypothesis.hypothesis_id,
                search_kind=draft.search_kind,
                description=draft.description,
                parameter_set=draft.parameter_set,
                within_validity_domain=draft.within_validity_domain,
            )
        )
    return out
