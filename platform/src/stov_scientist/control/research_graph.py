"""Main ResearchGraph (spec §38, §42-§43).

    research_intake -> scope_gate -> problem_formalization -> initial_ontology
    -> literature_research -> evidence_extraction -> ontology_refinement
    -> gap_analysis -> hypothesis_generation -> rival_generation
    -> prediction_derivation -> hypothesis_gate -> mechanism_exploration
    -> model_route_selector -> analytical_model | numerical_model
    -> model_assembly -> validation_graph -> model_gate -> simulation_planning
    -> solver_selection -> simulation_graph -> observable_extraction
    -> counterexample_search -> contradiction_evaluation -> evidence_update
    -> claim_synthesis -> scientific_judge -> final_claim_gate -> audit_bundle
    -> END

Human gates (spec §42): SCOPE, HYPOTHESIS_DIRECTION, FINAL_CLAIM — LangGraph
interrupt() with APPROVE / EDIT / REJECT + resume.

All loops are bounded by AcceptancePolicy (spec §43): max_model_revisions,
max_simulation_retries, max_research_iterations. Exceeding a bound ->
HUMAN_REVIEW_REQUIRED. Deep Agents are called only where the control plane
decides; they can never bypass validation (spec principle 12).
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from stov_scientist.control.fallbacks import (
    template_claims,
    template_hypotheses,
    template_mechanism,
)
from stov_scientist.control.ontology_helpers import default_stov_ontology
from stov_scientist.control.routers import select_model_route
from stov_scientist.control.services import ServiceBundle, build_default_services
from stov_scientist.control.simulation_graph import simulation_graph
from stov_scientist.control.spec_builder import build_simulation_spec
from stov_scientist.control.state import ResearchState
from stov_scientist.control.validation_graph import validation_graph
from stov_scientist.physics.model_templates import stov_linear_vortex_model
from stov_scientist.schemas import (
    AcceptancePolicy,
    CampaignStatus,
    ClaimStatus,
    EvidenceSet,
    GateDecision,
    HumanDecision,
    HypothesisCandidate,
    HypothesisStatus,
    MechanismCandidate,
    ModelType,
    ResearchCampaign,
    ResearchProblem,
    ScientificClaim,
    ScientificJudgement,
    ScientificModelSpec,
    ScientificOntology,
    SimulationRun,
    SimulationSpec,
    ValidationReport,
    utcnow,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _services(config) -> ServiceBundle:
    return config["configurable"]["services"]


def _campaigns(config):
    return _services(config).campaigns


def _llm(config, kind: str):
    services = _services(config)
    return services.main_model if kind == "main" else services.fast_model


def _try_llm(config, kind: str, fn, fallback):
    """Run an LLM-backed call; any failure degrades to the deterministic
    fallback with a warning recorded in the pipeline status."""
    model = _llm(config, kind)
    if model is None:
        return fallback, "no LLM configured; deterministic fallback used"
    try:
        return fn(model), ""
    except Exception as exc:
        return fallback, f"LLM call failed ({type(exc).__name__}: {exc}); deterministic fallback used"


def _stage(state: ResearchState, name: str, status: str) -> dict:
    pipeline = dict(state.get("pipeline_status") or {})
    pipeline[name] = status
    return {"current_stage": name, "pipeline_status": pipeline}


def _add_warning(state: ResearchState, warning: str) -> dict:
    return {"warnings": [*list(state.get("warnings") or []), warning]}


# ---------------------------------------------------------------------------
# nodes
# ---------------------------------------------------------------------------


def research_intake(state: ResearchState, config) -> dict:
    """Create the campaign from the user's request (Gate 0 — input only)."""
    campaigns = _campaigns(config)
    last = state["messages"][-1]
    text = _message_text(last)

    payload: dict[str, Any] = {}
    if text.strip().startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = {"research_question": text}

    question = str(payload.get("research_question") or text).strip()
    campaign_id = str(payload.get("campaign_id") or _derive_campaign_id(question))
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,127}$", campaign_id):
        campaign_id = _derive_campaign_id(question)

    problem = ResearchProblem(
        problem_id=f"prob-{campaign_id}",
        title=str(payload.get("title") or question[:120]),
        research_question=question,
        system_under_study=str(
            payload.get("system_under_study") or "space-time optical vortex field"
        ),
        scope=str(payload.get("scope") or "to be approved at Gate 1"),
        excluded_scope=str(payload.get("excluded_scope") or ""),
        target_observables=list(payload.get("target_observables") or []),
        known_constraints=list(payload.get("known_constraints") or []),
        unknowns=list(payload.get("unknowns") or []),
        owner=str(payload.get("owner") or "human"),
        kind=payload.get("kind") or "MIXED_THEORY_SIMULATION",
    )

    from stov_scientist.schemas import ConvergenceRule

    policy = AcceptancePolicy(
        policy_id=f"policy-{campaign_id}",
        required_observables=problem.target_observables or ["topological_charge"],
        convergence_rules=[
            ConvergenceRule(
                rule_id="default-convergence",
                metric="refinement_relative_change",
                target=0.05,
                min_refinements=1,
                note="campaign default: 5% relative change between refinement levels",
            )
        ],
        max_model_revisions=int(payload.get("max_model_revisions") or 3),
        max_simulation_retries=int(payload.get("max_simulation_retries") or 2),
        max_research_iterations=int(payload.get("max_research_iterations") or 3),
        final_human_approval_required=True,
    )
    campaign = ResearchCampaign(
        campaign_id=campaign_id,
        title=problem.title,
        research_problem=problem,
        acceptance_policy=policy,
        status=CampaignStatus.ACTIVE,
        owner=problem.owner,
    )
    campaigns.save_campaign(campaign)
    campaigns.save_object(campaign_id, "research_problem", problem)

    return {
        **_stage(state, "research_intake", "PASSED"),
        "campaign_id": campaign_id,
        "research_problem_id": problem.problem_id,
        "max_model_revisions": policy.max_model_revisions,
        "max_simulation_retries": policy.max_simulation_retries,
        "max_research_iterations": policy.max_research_iterations,
        "gate_status": "WAITING_SCOPE",
    }


def scope_gate(state: ResearchState, config) -> dict:
    """Gate 1 — Research Scope Approval (interrupt)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    decision_payload = interrupt(
        {
            "gate": "SCOPE",
            "title": "Gate 1 — Research Scope Approval",
            "object": problem.model_dump(mode="json"),
            "options": ["APPROVE", "EDIT", "REJECT"],
        }
    )
    decision = str(decision_payload.get("decision", "REJECT")).upper()
    rationale = str(decision_payload.get("rationale", ""))
    campaign = campaigns.load_campaign(campaign_id)

    if decision == "REJECT":
        _record_decision(campaigns, campaign, "SCOPE", problem.problem_id, GateDecision.REJECT, rationale)
        return {
            "stop_reason": "REJECTED",
            "gate_status": "NONE",
            **_stage(state, "scope_gate", "REJECTED"),
        }
    if decision == "EDIT":
        edited = decision_payload.get("edited_problem")
        if edited:
            try:
                merged = problem.model_dump()
                merged.update(edited)
                problem = ResearchProblem.model_validate(merged)
                campaigns.save_object(campaign_id, "research_problem", problem)
            except Exception as exc:
                return {
                    **_add_warning(state, f"Gate 1 EDIT payload invalid ({exc}); keeping original"),
                    **_stage(state, "scope_gate", "PASSED_WITH_WARNING"),
                    "gate_status": "NONE",
                }
    _record_decision(
        campaigns, campaign, "SCOPE", problem.problem_id,
        GateDecision(decision), rationale,
    )
    return {**_stage(state, "scope_gate", "PASSED"), "gate_status": "NONE"}


def problem_formalization(state: ResearchState, config) -> dict:
    """Formalize the research problem (LLM; deterministic fallback)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)

    def formalize(model) -> ResearchProblem:
        messages = [
            SystemMessage(
                content=(
                    "Formalize this research problem for the STOV AI Scientist "
                    "pipeline. Fill scope, excluded_scope, target_observables, "
                    "known_constraints, unknowns. Return JSON only, keys: title, "
                    "system_under_study, scope, excluded_scope, "
                    "target_observables (list), known_constraints (list), "
                    "unknowns (list). Do not change research_question or kind."
                )
            ),
            HumanMessage(content=problem.model_dump_json()),
        ]
        raw = model.invoke(messages)
        data = json.loads(_message_text(raw))
        merged = problem.model_dump()
        for key in (
            "title", "system_under_study", "scope", "excluded_scope",
            "target_observables", "known_constraints", "unknowns",
        ):
            if key in data:
                merged[key] = data[key]
        return ResearchProblem.model_validate(merged)

    problem, warning = _try_llm(config, "fast", formalize, problem)
    campaigns.save_object(campaign_id, "research_problem", problem)
    result = {**_stage(state, "problem_formalization", "PASSED")}
    if warning:
        result.update(_add_warning(state, warning))
    return result


def initial_ontology(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    ontology = default_stov_ontology(
        ontology_id=f"ontology-{campaign_id}",
        problem_observables=problem.target_observables,
    )
    campaigns.save_object(campaign_id, "ontology", ontology)
    return {
        **_stage(state, "initial_ontology", "PASSED"),
        "ontology_id": ontology.ontology_id,
    }


def literature_research(state: ResearchState, config) -> dict:
    """Deterministic literature search inside a documented SearchBoundary."""
    from stov_scientist.workers.literature import run_literature_search

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    queries = [problem.research_question]
    if problem.title != problem.research_question:
        queries.append(problem.title)
    queries.extend(o for o in problem.target_observables[:3])

    injected_clients = _services(config).extra.get("literature_clients")
    evidence = run_literature_search(
        problem,
        campaign_id=campaign_id,
        evidence_set_id=f"ev-{campaign_id}",
        boundary_id=f"boundary-{campaign_id}",
        queries=queries,
        clients=injected_clients,
    )
    if evidence is None or not evidence.records:
        return {
            **_stage(state, "literature_research", "NO_RECORDS_IN_BOUNDARY"),
            "evidence_set_id": f"ev-{campaign_id}",
            "search_boundary_id": f"boundary-{campaign_id}",
        }
    campaigns.save_object(campaign_id, "evidence_set", evidence)
    campaigns.save_object(campaign_id, "search_boundary", evidence.search_boundaries[0])
    return {
        **_stage(state, "literature_research", "PASSED"),
        "evidence_set_id": evidence.evidence_set_id,
        "search_boundary_id": evidence.search_boundaries[0].search_boundary_id,
    }


def evidence_extraction(state: ResearchState, config) -> dict:
    """Register evidence records in the ledger (dedup already applied)."""
    campaigns = _campaigns(config)
    services = _services(config)
    campaign_id = state["campaign_id"]
    evidence = campaigns.load_object(campaign_id, "evidence_set", schema=EvidenceSet)
    if evidence is None:
        return {**_stage(state, "evidence_extraction", "EMPTY")}
    ledger = services.evidence
    assert ledger is not None, "ServiceBundle.evidence not configured"
    for record in evidence.records:
        ledger.add_record(record, evidence.evidence_set_id)
    campaigns.save_object(campaign_id, "evidence_set", evidence)
    return {**_stage(state, "evidence_extraction", "PASSED")}


def ontology_refinement(state: ResearchState, config) -> dict:
    """Refine ontology with evidence (deterministic v1: keep default)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    ontology = campaigns.load_object(campaign_id, "ontology", schema=ScientificOntology)
    evidence = campaigns.load_object(campaign_id, "evidence_set", schema=EvidenceSet)
    if ontology is None:
        ontology = default_stov_ontology(ontology_id=f"ontology-{campaign_id}")
    if evidence and evidence.records:
        seen_concepts = {c.name for c in ontology.concepts}
        additions = []
        for record in evidence.records[:5]:
            if record.title not in seen_concepts:
                additions.append(record.title[:80])
        if additions:
            ontology.known_constraints = [
                *list(ontology.known_constraints),
                f"evidence retrieved (search boundary {evidence.search_boundaries[0].search_boundary_id if evidence.search_boundaries else '?'}): {', '.join(additions)}",
            ]
    campaigns.save_object(campaign_id, "ontology", ontology)
    return {**_stage(state, "ontology_refinement", "PASSED")}


def gap_analysis(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    evidence = campaigns.load_object(campaign_id, "evidence_set", schema=EvidenceSet)
    gaps: list[str] = []
    if problem.target_observables:
        covered = 0
        haystack = " ".join((r.title + " " + r.summary).lower() for r in (evidence.records if evidence else []))
        for obs in problem.target_observables:
            if obs.lower() in haystack:
                covered += 1
            else:
                gaps.append(f"observable {obs!r} not located within the documented search boundary")
        status = "PASSED" if not gaps else "GAPS_RECORDED"
    else:
        gaps.append("no target observables declared")
        status = "GAPS_RECORDED"
    campaigns.save_object(campaign_id, "gap_analysis", {"gaps": gaps})
    result = {**_stage(state, "gap_analysis", status)}
    return result


def hypothesis_generation(state: ResearchState, config) -> dict:
    from stov_scientist.workers.hypothesis import generate_hypotheses

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    evidence = campaigns.load_object(campaign_id, "evidence_set", schema=EvidenceSet)

    def generate(model):
        return generate_hypotheses(model, problem, evidence)

    hypotheses, warning = _try_llm(
        config, "main", generate, template_hypotheses(problem)
    )
    if not hypotheses:
        hypotheses = template_hypotheses(problem)
        warning = warning or "worker produced no hypotheses; template used"
    campaigns.save_object(campaign_id, "hypotheses", hypotheses)
    result = {
        **_stage(state, "hypothesis_generation", "PASSED"),
        "hypothesis_set_id": f"hs-{campaign_id}",
    }
    if warning:
        result.update(_add_warning(state, warning))
    return result


def rival_generation(state: ResearchState, config) -> dict:
    """Deterministic check: every hypothesis must have a rival (spec §38)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    hypotheses = campaigns.load_object(campaign_id, "hypotheses") or []
    hypotheses = [HypothesisCandidate.model_validate(h) for h in hypotheses]
    for h in hypotheses:
        if not h.rival_hypothesis_ids:
            h.rival_hypothesis_ids = [
                r.hypothesis_id for r in hypotheses if r.hypothesis_id != h.hypothesis_id
            ]
    campaigns.save_object(campaign_id, "hypotheses", hypotheses)
    return {**_stage(state, "rival_generation", "PASSED")}


def prediction_derivation(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    hypotheses = campaigns.load_object(campaign_id, "hypotheses") or []
    hypotheses = [HypothesisCandidate.model_validate(h) for h in hypotheses]
    missing = [h.hypothesis_id for h in hypotheses if not h.predictions]
    campaigns.save_object(campaign_id, "hypotheses", hypotheses)
    status = "PASSED" if not missing else "MISSING_PREDICTIONS"
    result = {**_stage(state, "prediction_derivation", status)}
    if missing:
        result.update(_add_warning(state, f"hypotheses without predictions: {missing}"))
    return result


def hypothesis_gate(state: ResearchState, config) -> dict:
    """Gate 2 — Hypothesis / Model Direction Approval (interrupt)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    hypotheses = campaigns.load_object(campaign_id, "hypotheses") or []
    hypotheses = [HypothesisCandidate.model_validate(h) for h in hypotheses]
    decision_payload = interrupt(
        {
            "gate": "HYPOTHESIS_DIRECTION",
            "title": "Gate 2 — Hypothesis / Model Direction Approval",
            "object": [h.model_dump(mode="json") for h in hypotheses],
            "options": ["APPROVE", "EDIT", "REJECT"],
        }
    )
    decision = str(decision_payload.get("decision", "REJECT")).upper()
    rationale = str(decision_payload.get("rationale", ""))
    campaign = campaigns.load_campaign(campaign_id)

    if decision == "REJECT":
        _record_decision(campaigns, campaign, "HYPOTHESIS_DIRECTION", "hypotheses", GateDecision.REJECT, rationale)
        return {
            "stop_reason": "REJECTED",
            "gate_status": "NONE",
            **_stage(state, "hypothesis_gate", "REJECTED"),
        }
    if decision == "EDIT":
        edited = decision_payload.get("edited_hypotheses")
        if edited:
            try:
                hypotheses = [HypothesisCandidate.model_validate(h) for h in edited]
                campaigns.save_object(campaign_id, "hypotheses", hypotheses)
            except Exception as exc:
                return {
                    **_add_warning(state, f"Gate 2 EDIT payload invalid ({exc}); keeping original"),
                    **_stage(state, "hypothesis_gate", "PASSED_WITH_WARNING"),
                    "gate_status": "NONE",
                }
    selected = [str(i) for i in decision_payload.get("selected_hypothesis_ids", [])]
    if not selected:
        selected = [h.hypothesis_id for h in hypotheses[:1]]
    for h in hypotheses:
        h.status = (
            HypothesisStatus.SELECTED_FOR_TEST
            if h.hypothesis_id in selected
            else HypothesisStatus.UNDER_REVIEW
        )
    campaigns.save_object(campaign_id, "hypotheses", hypotheses)
    _record_decision(
        campaigns, campaign, "HYPOTHESIS_DIRECTION", "hypotheses",
        GateDecision(decision), rationale,
    )
    return {
        **_stage(state, "hypothesis_gate", "PASSED"),
        "gate_status": "NONE",
        "selected_hypothesis_ids": selected,
    }


def mechanism_exploration(state: ResearchState, config) -> dict:
    from stov_scientist.workers.mechanism import generate_mechanisms

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    hypotheses = campaigns.load_object(campaign_id, "hypotheses") or []
    hypotheses = [HypothesisCandidate.model_validate(h) for h in hypotheses]
    selected = [
        h for h in hypotheses if h.hypothesis_id in (state.get("selected_hypothesis_ids") or [])
    ] or hypotheses[:1]

    mechanisms: list[MechanismCandidate] = []
    warnings: list[str] = []
    for hypothesis in selected:
        def generate(model, hyp=hypothesis):
            return generate_mechanisms(model, hyp)

        found, warning = _try_llm(
            config, "main", generate, [template_mechanism(
                _problem(config, campaign_id), hypothesis
            )]
        )
        mechanisms.extend(found)
        if warning:
            warnings.append(warning)
    campaigns.save_object(campaign_id, "mechanisms", mechanisms)
    result = {
        **_stage(state, "mechanism_exploration", "PASSED"),
        "mechanism_set_id": f"ms-{campaign_id}",
    }
    if warnings:
        result.update(_add_warning(state, "; ".join(warnings)))
    return result


def model_route_selector(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    route, warnings = select_model_route(problem)
    result = {
        **_stage(state, "model_route_selector", route),
        "model_route": route,
    }
    if warnings:
        result.update(_add_warning(state, "; ".join(warnings)))
    return result


def analytical_model(state: ResearchState, config) -> dict:
    return _draft_model(state, config, analytical=True)


def numerical_model(state: ResearchState, config) -> dict:
    return _draft_model(state, config, analytical=False)


def _draft_model(state: ResearchState, config, *, analytical: bool) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    model = stov_linear_vortex_model(model_id=f"model-{campaign_id}")
    if not analytical:
        model.model_type = ModelType.NUMERICAL
        model.numerical_assumptions = [
            *list(model.numerical_assumptions),
            "grid refinement per campaign convergence rule",
            "ensemble seeds per uncertainty plan",
        ]
    campaigns.save_object(campaign_id, "model_spec", model)
    return {
        **_stage(state, "analytical_model" if analytical else "numerical_model", "PASSED"),
        "model_spec_id": model.model_id,
    }


def model_assembly(state: ResearchState, config) -> dict:
    """Deterministic assembly: conventions + validity domain must be
    present (they are, via the validated template)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    model = campaigns.load_object(campaign_id, "model_spec", schema=ScientificModelSpec)
    if model is None:
        model = stov_linear_vortex_model(model_id=f"model-{campaign_id}")
        campaigns.save_object(campaign_id, "model_spec", model)
    return {**_stage(state, "model_assembly", "PASSED")}


def model_gate(state: ResearchState, config) -> dict:
    """Route after validation: PASS -> simulation; REVISE -> bounded loop;
    else -> HUMAN_REVIEW_REQUIRED."""
    action = state.get("validation_action", "")
    revision_count = state.get("model_revision_count", 0)
    max_revisions = state.get("max_model_revisions", 3)
    if state.get("validation_passed"):
        return {**_stage(state, "model_gate", "PASSED")}
    if action == "REVISE_MODEL" and revision_count < max_revisions:
        return {
            **_stage(state, "model_gate", "REVISE_MODEL"),
            "model_revision_count": revision_count + 1,
            "iteration": state.get("iteration", 0) + 1,
        }
    return {
        **_stage(state, "model_gate", "HUMAN_REVIEW_REQUIRED"),
        "gate_status": "HUMAN_REVIEW_REQUIRED",
        "stop_reason": "LIMIT_REACHED",
    }


def simulation_planning(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    problem = campaigns.load_object(campaign_id, "research_problem", schema=ResearchProblem)
    model = campaigns.load_object(campaign_id, "model_spec", schema=ScientificModelSpec)
    campaign = campaigns.load_campaign(campaign_id)
    spec = build_simulation_spec(
        model,
        problem,
        simulation_id=f"sim-{campaign_id}",
        policy=campaign.acceptance_policy if campaign else None,
    )
    campaigns.save_object(campaign_id, "simulation_spec", spec)
    return {
        **_stage(state, "simulation_planning", "PASSED"),
        "simulation_spec_id": spec.simulation_id,
    }


def solver_selection(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    services = _services(config)
    campaign_id = state["campaign_id"]
    model = campaigns.load_object(campaign_id, "model_spec", schema=ScientificModelSpec)
    spec = campaigns.load_object(campaign_id, "simulation_spec", schema=SimulationSpec)
    from stov_scientist.simulation.selector import select_solver

    simulation_runner = services.simulation
    assert simulation_runner is not None, "ServiceBundle.simulation not configured"
    selection = select_solver(model, spec, simulation_runner.registry)
    if not selection.is_valid:
        result = {
            **_stage(state, "solver_selection", "NO_VALID_SOLVER"),
            "solver_valid": False,
            "contradiction_kind": "INDETERMINATE",
        }
        result.update(
            _add_warning(state, f"NO_VALID_SOLVER: {selection.selection_reason}")
        )
        return result
    spec.solver_id = selection.solver_id
    campaigns.save_object(campaign_id, "simulation_spec", spec)
    return {
        **_stage(state, "solver_selection", "PASSED"),
        "solver_valid": True,
        "retry_count": 0,
        "max_retries": state.get("max_simulation_retries", 2),
        "contradiction_kind": "",
    }


def observable_extraction(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    observables = campaigns.load_object(campaign_id, "observables")
    run = campaigns.load_object(campaign_id, "simulation_run", schema=SimulationRun)
    if run is not None:
        run_ids = list(state.get("simulation_run_ids") or [])
        if run.run_id not in run_ids:
            run_ids.append(run.run_id)
        summary = observables if observables else {}
        return {
            **_stage(state, "observable_extraction", "PASSED" if summary else "EMPTY"),
            "simulation_run_ids": run_ids,
        }
    return {**_stage(state, "observable_extraction", "SKIPPED")}


def counterexample_search(state: ResearchState, config) -> dict:
    from stov_scientist.workers.counterexample import (
        boundary_cases,
        numerical_stress_cases,
    )

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    model = campaigns.load_object(campaign_id, "model_spec", schema=ScientificModelSpec)
    spec = campaigns.load_object(campaign_id, "simulation_spec", schema=SimulationSpec)
    candidates = boundary_cases(model)
    if spec is not None:
        candidates += numerical_stress_cases(spec)
    campaigns.save_object(campaign_id, "counterexamples", candidates)
    return {
        **_stage(state, "counterexample_search", "PASSED"),
        "counterexample_set_id": f"cx-{campaign_id}",
    }


def contradiction_evaluation(state: ResearchState, config) -> dict:
    """Evaluate contradictions produced during simulation (spec PHASE 11)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    kinds: list[str] = []
    if state.get("contradiction_kind"):
        kinds.append(state["contradiction_kind"])
    if not state.get("completed", False) and state.get("run_status"):
        kinds.append(state.get("contradiction_kind") or "INDETERMINATE")
    campaigns.save_object(campaign_id, "contradiction_kinds", kinds)
    status = "CLEAN" if not kinds else "CONTRADICTIONS_RECORDED"
    result = {**_stage(state, "contradiction_evaluation", status)}
    if kinds:
        result.update(
            _add_warning(
                state,
                f"contradiction classification: {kinds} — "
                "numerical failures are NOT physical contradictions",
            )
        )
    return result


def evidence_update(state: ResearchState, config) -> dict:
    """Update claim/evidence relations in the ledger (deterministic)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    evidence = campaigns.load_object(campaign_id, "evidence_set", schema=EvidenceSet)
    supporting: list[str] = []
    contradicting: list[str] = []
    for record in (evidence.records if evidence else []):
        if record.relation.value == "SUPPORT":
            supporting.append(record.evidence_id)
        elif record.relation.value == "CONTRADICT":
            contradicting.append(record.evidence_id)
    campaigns.save_object(
        campaign_id,
        "evidence_relations",
        {"supporting": supporting, "contradicting": contradicting},
    )
    return {**_stage(state, "evidence_update", "PASSED")}


def claim_synthesis(state: ResearchState, config) -> dict:
    from stov_scientist.workers.synthesis import synthesize_claims

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    model = campaigns.load_object(campaign_id, "model_spec", schema=ScientificModelSpec)
    run = campaigns.load_object(campaign_id, "simulation_run", schema=SimulationRun)
    relations = campaigns.load_object(campaign_id, "evidence_relations") or {}

    def synthesize(model_llm):
        return synthesize_claims(
            model_llm,
            campaign_id=campaign_id,
            model_spec=model,
            simulation_runs=[run] if run else [],
            judgements=[],
            evidence_ids_supporting=relations.get("supporting", []),
            evidence_ids_contradicting=relations.get("contradicting", []),
        )

    claims, warning = _try_llm(
        config,
        "main",
        synthesize,
        template_claims(
            campaign_id=campaign_id,
            model=model,
            runs=[run] if run else [],
            evidence_ids=relations.get("supporting", []),
        ),
    )
    campaigns.save_object(campaign_id, "claims", claims)
    result = {
        **_stage(state, "claim_synthesis", "PASSED"),
        "claim_bundle_id": f"claims-{campaign_id}",
    }
    if warning:
        result.update(_add_warning(state, warning))
    return result


def scientific_judge(state: ResearchState, config) -> dict:
    from stov_scientist.evidence.judge import JudgeInputs, judge

    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    claims = campaigns.load_object(campaign_id, "claims") or []
    claims = [ScientificClaim.model_validate(c) for c in claims]
    run = campaigns.load_object(campaign_id, "simulation_run", schema=SimulationRun)
    validation_report = campaigns.load_object(
        campaign_id, "validation_report", schema=ValidationReport
    )
    relations = campaigns.load_object(campaign_id, "evidence_relations") or {}
    campaign = campaigns.load_campaign(campaign_id)

    judgements: list[ScientificJudgement] = []
    for claim in claims:
        inputs = JudgeInputs(
            claim=claim,
            policy=campaign.acceptance_policy if campaign else None,
            validation_reports=[validation_report] if validation_report else [],
            contradictions=[],
            simulation_converged=(
                run.convergence_result.achieved
                if run and run.convergence_result
                else None
            ),
            evidence_count=(
                len(relations.get("supporting", [])),
                len(relations.get("contradicting", [])),
            ),
            provenance_complete=bool(validation_report),
            reproducibility_ok=run is not None,
        )
        judgement = judge(inputs)
        claim.status = {
            "SUPPORTED_WITHIN_SCOPE": ClaimStatus.SUPPORTED_WITHIN_SCOPE,
            "PARTIALLY_SUPPORTED": ClaimStatus.PARTIALLY_SUPPORTED,
            "INCONCLUSIVE": ClaimStatus.INCONCLUSIVE,
            "CONTRADICTED": ClaimStatus.CONTRADICTED,
            "INSUFFICIENT_EVIDENCE": ClaimStatus.INSUFFICIENT_EVIDENCE,
        }[judgement.status.value]
        judgements.append(judgement)

    campaigns.save_object(campaign_id, "claims", claims)
    campaigns.save_object(campaign_id, "judgements", judgements)
    return {
        **_stage(state, "scientific_judge", "PASSED"),
        "judgement_ids": [j.judgement_id for j in judgements],
    }


def final_claim_gate(state: ResearchState, config) -> dict:
    """Gate 3 — Final Scientific Claim Approval (interrupt)."""
    campaigns = _campaigns(config)
    campaign_id = state["campaign_id"]
    claims = campaigns.load_object(campaign_id, "claims") or []
    claims = [ScientificClaim.model_validate(c) for c in claims]
    judgements = campaigns.load_object(campaign_id, "judgements") or []
    judgements = [ScientificJudgement.model_validate(j) for j in judgements]

    decision_payload = interrupt(
        {
            "gate": "FINAL_CLAIM",
            "title": "Gate 3 — Final Scientific Claim Approval",
            "object": {
                "claims": [c.model_dump(mode="json") for c in claims],
                "judgements": [j.model_dump(mode="json") for j in judgements],
            },
            "options": ["APPROVE", "EDIT", "REJECT"],
        }
    )
    decision = str(decision_payload.get("decision", "APPROVE")).upper()
    rationale = str(decision_payload.get("rationale", ""))
    campaign = campaigns.load_campaign(campaign_id)

    if decision == "EDIT":
        edited = decision_payload.get("edited_claims")
        if edited:
            try:
                claims = [ScientificClaim.model_validate(c) for c in edited]
                campaigns.save_object(campaign_id, "claims", claims)
            except Exception as exc:
                return {
                    **_add_warning(state, f"Gate 3 EDIT payload invalid ({exc})"),
                    **_stage(state, "final_claim_gate", "PASSED_WITH_WARNING"),
                    "gate_status": "NONE",
                }
    if decision == "REJECT":
        _record_decision(campaigns, campaign, "FINAL_CLAIM", "claims", GateDecision.REJECT, rationale)
        return {
            **_stage(state, "final_claim_gate", "REJECTED"),
            "gate_status": "NONE",
            "stop_reason": "INCONCLUSIVE",
        }
    _record_decision(campaigns, campaign, "FINAL_CLAIM", "claims", GateDecision(decision), rationale)
    return {
        **_stage(state, "final_claim_gate", "PASSED"),
        "gate_status": "NONE",
        "stop_reason": state.get("stop_reason") or "COMPLETED",
    }


def audit_bundle(state: ResearchState, config) -> dict:
    campaigns = _campaigns(config)
    services = _services(config)
    campaign_id = state["campaign_id"]
    campaign = campaigns.load_campaign(campaign_id)
    if campaign is None:
        return {**_stage(state, "audit_bundle", "FAILED")}

    def load(kind, schema=None):
        return campaigns.load_object(campaign_id, kind, schema=schema)

    evidence = load("evidence_set", EvidenceSet)
    pipeline = dict(state.get("pipeline_status") or {})
    pipeline["stop_reason"] = state.get("stop_reason") or "COMPLETED"
    audits = campaigns.write_audit_bundle(
        campaign_id,
        campaign=campaign,
        problem=load("research_problem"),
        ontology=load("ontology"),
        boundary=load("search_boundary"),
        evidence_records=evidence.records if evidence else [],
        hypotheses=load("hypotheses"),
        mechanisms=load("mechanisms"),
        model_spec=load("model_spec"),
        validation_report=load("validation_report"),
        simulation_specs=[load("simulation_spec")] if load("simulation_spec") else [],
        simulation_runs=[load("simulation_run")] if load("simulation_run") else [],
        counterexamples=load("counterexamples"),
        claims=load("claims"),
        judgements=load("judgements"),
        artifact_manifest=[
            a.model_dump(mode="json")
            for a in _require_artifacts(services).list_artifacts(campaign_id)
        ],
        pipeline_status=pipeline,
        warnings=state.get("warnings") or [],
    )
    if state.get("stop_reason") not in ("REJECTED",):
        campaign.status = CampaignStatus.COMPLETED
        campaigns.save_campaign(campaign)
    return {
        **_stage(state, "audit_bundle", "PASSED"),
        "audit_bundle_id": str(audits),
    }


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _message_text(message) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, list):
        return " ".join(str(part) for part in content)
    return str(content)


def _derive_campaign_id(question: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", question.lower()).strip("-")[:40]
    return f"campaign-{slug}" if slug else "campaign-default"


def _record_decision(campaigns, campaign, gate: str, object_id: str, decision: GateDecision, rationale: str) -> None:
    if campaign is None:
        return
    campaign.human_decisions = [
        *list(campaign.human_decisions),
        HumanDecision(
            decision_id=f"dec-{gate}-{len(campaign.human_decisions) + 1}",
            gate=gate,
            object_id=object_id,
            decision=decision,
            rationale=rationale,
            decided_by="human",
            decided_at=utcnow(),
        ),
    ]
    campaigns.save_campaign(campaign)


def _problem(config, campaign_id: str) -> ResearchProblem:
    return _campaigns(config).load_object(
        campaign_id, "research_problem", schema=ResearchProblem
    )


def _require_artifacts(services):
    from stov_scientist.artifacts.registry import ArtifactRegistry

    artifacts = services.artifacts
    assert isinstance(artifacts, ArtifactRegistry), "ServiceBundle.artifacts not configured"
    return artifacts


# ---------------------------------------------------------------------------
# routing
# ---------------------------------------------------------------------------


def route_after_scope(state: ResearchState) -> str:
    return "end" if state.get("stop_reason") == "REJECTED" else "continue"


def route_model_kind(state: ResearchState) -> str:
    return "analytical" if state.get("model_route") == "ANALYTICAL" else "numerical"


def route_after_validation(state: ResearchState) -> str:
    if state.get("validation_passed"):
        return "simulation"
    if state.get("stop_reason") == "LIMIT_REACHED":
        return "judge"
    return "revise"


def route_after_solver(state: ResearchState) -> str:
    return "simulation" if state.get("solver_valid", False) else "skip_simulation"


def route_after_hypothesis_gate(state: ResearchState) -> str:
    return "end" if state.get("stop_reason") == "REJECTED" else "continue"


# ---------------------------------------------------------------------------
# graph construction
# ---------------------------------------------------------------------------


def build_research_graph(services: ServiceBundle | None = None):
    builder = StateGraph(ResearchState)

    builder.add_node("research_intake", research_intake)
    builder.add_node("scope_gate", scope_gate)
    builder.add_node("problem_formalization", problem_formalization)
    builder.add_node("initial_ontology", initial_ontology)
    builder.add_node("literature_research", literature_research)
    builder.add_node("evidence_extraction", evidence_extraction)
    builder.add_node("ontology_refinement", ontology_refinement)
    builder.add_node("gap_analysis", gap_analysis)
    builder.add_node("hypothesis_generation", hypothesis_generation)
    builder.add_node("rival_generation", rival_generation)
    builder.add_node("prediction_derivation", prediction_derivation)
    builder.add_node("hypothesis_gate", hypothesis_gate)
    builder.add_node("mechanism_exploration", mechanism_exploration)
    builder.add_node("model_route_selector", model_route_selector)
    builder.add_node("analytical_model", analytical_model)
    builder.add_node("numerical_model", numerical_model)
    builder.add_node("model_assembly", model_assembly)
    builder.add_node("validation_graph", validation_graph)
    builder.add_node("model_gate", model_gate)
    builder.add_node("simulation_planning", simulation_planning)
    builder.add_node("solver_selection", solver_selection)
    builder.add_node("simulation_graph", simulation_graph)
    builder.add_node("observable_extraction", observable_extraction)
    builder.add_node("counterexample_search", counterexample_search)
    builder.add_node("contradiction_evaluation", contradiction_evaluation)
    builder.add_node("evidence_update", evidence_update)
    builder.add_node("claim_synthesis", claim_synthesis)
    builder.add_node("scientific_judge", scientific_judge)
    builder.add_node("final_claim_gate", final_claim_gate)
    builder.add_node("audit_bundle", audit_bundle)

    builder.add_edge(START, "research_intake")
    builder.add_edge("research_intake", "scope_gate")
    builder.add_conditional_edges(
        "scope_gate",
        route_after_scope,
        {"continue": "problem_formalization", "end": "audit_bundle"},
    )
    builder.add_edge("problem_formalization", "initial_ontology")
    builder.add_edge("initial_ontology", "literature_research")
    builder.add_edge("literature_research", "evidence_extraction")
    builder.add_edge("evidence_extraction", "ontology_refinement")
    builder.add_edge("ontology_refinement", "gap_analysis")
    builder.add_edge("gap_analysis", "hypothesis_generation")
    builder.add_edge("hypothesis_generation", "rival_generation")
    builder.add_edge("rival_generation", "prediction_derivation")
    builder.add_edge("prediction_derivation", "hypothesis_gate")
    builder.add_conditional_edges(
        "hypothesis_gate",
        route_after_hypothesis_gate,
        {"continue": "mechanism_exploration", "end": "audit_bundle"},
    )
    builder.add_edge("mechanism_exploration", "model_route_selector")
    builder.add_conditional_edges(
        "model_route_selector",
        route_model_kind,
        {"analytical": "analytical_model", "numerical": "numerical_model"},
    )
    builder.add_edge("analytical_model", "model_assembly")
    builder.add_edge("numerical_model", "model_assembly")
    builder.add_edge("model_assembly", "validation_graph")
    builder.add_edge("validation_graph", "model_gate")
    builder.add_conditional_edges(
        "model_gate",
        route_after_validation,
        {
            "simulation": "simulation_planning",
            "revise": "model_assembly",
            "judge": "claim_synthesis",
        },
    )
    builder.add_edge("simulation_planning", "solver_selection")
    builder.add_conditional_edges(
        "solver_selection",
        route_after_solver,
        {"simulation": "simulation_graph", "skip_simulation": "observable_extraction"},
    )
    builder.add_edge("simulation_graph", "observable_extraction")
    builder.add_edge("observable_extraction", "counterexample_search")
    builder.add_edge("counterexample_search", "contradiction_evaluation")
    builder.add_edge("contradiction_evaluation", "evidence_update")
    builder.add_edge("evidence_update", "claim_synthesis")
    builder.add_edge("claim_synthesis", "scientific_judge")
    builder.add_edge("scientific_judge", "final_claim_gate")
    builder.add_edge("final_claim_gate", "audit_bundle")
    builder.add_edge("audit_bundle", END)

    return builder


def graph_with_memory(services: ServiceBundle | None = None):
    """Compiled graph with an in-memory checkpointer (dev + tests, spec §51)."""
    from langgraph.checkpoint.memory import InMemorySaver

    return build_research_graph(services).compile(checkpointer=InMemorySaver())


def compile_default_graph():
    """Module-level graph for langgraph.json. Checkpointer is attached by the
    LangGraph server (dev uses its default; tests use graph_with_memory())."""
    return build_research_graph(build_default_services()).compile()


graph = compile_default_graph()
