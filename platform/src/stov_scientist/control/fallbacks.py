"""Deterministic fallbacks for LLM-backed nodes.

When no LLM is available (missing DEEPSEEK_API_KEY, test fake absent, or a
structured-output failure), nodes degrade to these honest deterministic
templates. Everything produced here is labelled as a template: hypothesis
status stays CANDIDATE, equation status stays CANDIDATE_MODEL unless the
template carries a validated source chain.
"""

from __future__ import annotations

from stov_scientist.schemas import (
    ClaimStatus,
    FalsificationCondition,
    HypothesisCandidate,
    HypothesisStatus,
    MechanismCandidate,
    Prediction,
    ResearchProblem,
    ScientificClaim,
    ScientificModelSpec,
    SimulationRun,
)


def template_hypotheses(problem: ResearchProblem) -> list[HypothesisCandidate]:
    """One primary + one rival template hypothesis derived from the problem
    statement — explicitly labelled, never presented as evidence."""
    primary = HypothesisCandidate(
        hypothesis_id=f"h-{problem.problem_id}-1",
        statement=(
            "The phase structure of the studied spatiotemporal optical field "
            "carries a well-defined topological charge in the (x, t) plane "
            "that is preserved under free-space propagation within the "
            "alias-free propagation domain (deterministic template hypothesis)."
        ),
        claim_type="BEHAVIOUR",
        status=HypothesisStatus.CANDIDATE,
        assumptions=[
            "linear scalar field",
            "paraxial propagation",
            "uniform grid, FFT-periodic boundaries",
        ],
        boundary_conditions=["vacuum propagation", "alias-free propagation distance"],
        predictions=[
            Prediction(
                prediction_id=f"p-{problem.problem_id}-1-1",
                hypothesis_id=f"h-{problem.problem_id}-1",
                observable="topological_charge",
                expected_outcome="integer charge, stable across propagation",
            )
        ],
        falsification_conditions=[
            FalsificationCondition(
                condition_id=f"fc-{problem.problem_id}-1-1",
                statement="measured (x,t) phase winding differs from the declared charge outside numerical uncertainty",
            )
        ],
        unknowns=["envelope phase structure beyond the linear ansatz"],
        testability="HIGH",
        computational_feasibility="HIGH",
    )
    rival = HypothesisCandidate(
        hypothesis_id=f"h-{problem.problem_id}-2",
        statement=(
            "The observed phase structure is an artifact of the sampling grid "
            "and does not represent a physical spatiotemporal vortex "
            "(deterministic rival template)."
        ),
        claim_type="BEHAVIOUR",
        status=HypothesisStatus.CANDIDATE,
        assumptions=["grid-dependent phase structure"],
        predictions=[
            Prediction(
                prediction_id=f"p-{problem.problem_id}-2-1",
                hypothesis_id=f"h-{problem.problem_id}-2",
                observable="topological_charge",
                expected_outcome="charge estimate changes with grid resolution beyond convergence tolerance",
            )
        ],
        falsification_conditions=[
            FalsificationCondition(
                condition_id=f"fc-{problem.problem_id}-2-1",
                statement="charge estimate is grid-convergent within the AcceptancePolicy rule",
            )
        ],
        unknowns=[],
        testability="HIGH",
        computational_feasibility="HIGH",
    )
    primary.rival_hypothesis_ids = [rival.hypothesis_id]
    rival.rival_hypothesis_ids = [primary.hypothesis_id]
    return [primary, rival]


def template_mechanism(
    problem: ResearchProblem, hypothesis: HypothesisCandidate
) -> MechanismCandidate:
    return MechanismCandidate(
        mechanism_id=f"mech-{hypothesis.hypothesis_id}-1",
        hypothesis_id=hypothesis.hypothesis_id,
        description=(
            "Phase singularity in the (x, t) plane: the vortex ansatz "
            "(x + i sgn(l) t)^|l| times a Gaussian envelope produces a "
            "winding phase whose charge is conserved in linear free-space "
            "propagation (deterministic template mechanism)."
        ),
        governing_principles=[
            "phase winding topology",
            "linear free-space propagation (angular spectrum)",
        ],
        assumptions=hypothesis.assumptions,
        boundary_conditions=hypothesis.boundary_conditions,
        predicted_observables=["topological_charge", "intensity"],
        evidence_ids=list(hypothesis.supporting_evidence_ids),
        model_requirements=["(x, t) field", "FFT grid", "propagation solver"],
    )


def template_claims(
    *,
    campaign_id: str,
    model: ScientificModelSpec | None,
    runs: list[SimulationRun],
    evidence_ids: list[str],
) -> list[ScientificClaim]:
    claims: list[ScientificClaim] = []
    converged = any(
        (r.convergence_result.achieved if r.convergence_result else False) for r in runs
    )
    if model is not None:
        claims.append(
            ScientificClaim(
                claim_id=f"claim-{campaign_id}-1",
                statement=(
                    f"Model {model.model_id!r} is internally consistent under "
                    "the deterministic validator chain within its declared "
                    "validity domain (template claim from pipeline facts)."
                ),
                scope=model.validity_domain.description,
                model_id=model.model_id,
                supporting_evidence_ids=evidence_ids,
                simulation_run_ids=[r.run_id for r in runs],
                assumptions=model.physical_assumptions,
                limitations=model.validity_domain.applicability_notes.split(".")[:2],
                status=ClaimStatus.UNASSESSED,
            )
        )
    if runs:
        statuses = [r.status.value for r in runs]
        claims.append(
            ScientificClaim(
                claim_id=f"claim-{campaign_id}-2",
                statement=(
                    f"Simulations executed with statuses {statuses}; "
                    f"numerical convergence achieved: {converged}. "
                    "This records the numerical outcome and implies no "
                    "physical conclusion beyond the model's validity domain."
                ),
                scope="numerical outcome record",
                simulation_run_ids=[r.run_id for r in runs],
                status=ClaimStatus.UNASSESSED,
            )
        )
    return claims
