"""Deep Agent research workers (spec PHASE 8). LangGraph stays the control
plane; these are bounded long-horizon workers with isolated skill sets."""

from stov_scientist.workers.base import WorkerConfig, WorkerResult, run_structured
from stov_scientist.workers.counterexample import (
    boundary_cases,
    explore_counterexamples,
    numerical_stress_cases,
)
from stov_scientist.workers.hypothesis import generate_hypotheses
from stov_scientist.workers.literature import classify_relations, run_literature_search
from stov_scientist.workers.mechanism import generate_mechanisms
from stov_scientist.workers.synthesis import synthesize_claims

__all__ = [
    "WorkerConfig",
    "WorkerResult",
    "boundary_cases",
    "classify_relations",
    "explore_counterexamples",
    "generate_hypotheses",
    "generate_mechanisms",
    "numerical_stress_cases",
    "run_literature_search",
    "run_structured",
    "synthesize_claims",
]
