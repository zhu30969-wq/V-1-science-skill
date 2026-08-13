"""End-to-end research graph tests (spec §69): happy path with the three
human gates (interrupt + resume), REJECT path, INCONCLUSIVE outcomes.

Fully offline: fake LLM + injected literature clients + local stores.

LangGraph 1.2 API note: interrupts surface in the returned state under
``__interrupt__`` (Interrupt objects with ``.value``); resume goes through
``Command(resume=...)``.
"""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from stov_scientist.control.services import ServiceBundle
from stov_scientist.literature.base import ClientResponse, LiteratureRecord
from stov_scientist.schemas import RetrievalStatus
from tests.fakes import scripted_model


class FakeLiteratureClient:
    def search(self, query, max_results=10):
        return ClientResponse(
            status=RetrievalStatus.COMPLETE,
            records=[
                LiteratureRecord(
                    title="Generation of spatiotemporal optical vortices",
                    authors=["A. Chong", "C. Wan", "J. Chen"],
                    year=2020,
                    doi="10.1038/s41566-020-0627-8",
                    source_database="fake",
                )
            ],
            total_hits=1,
        )

    def close(self):
        pass


PROBLEM_PAYLOAD = {
    "campaign_id": "campaign-e2e",
    "title": "STOV topology stability in vacuum",
    "research_question": "Is the topological charge of a spatiotemporal vortex preserved under free-space propagation?",
    "system_under_study": "linear STOV pulse",
    "scope": "vacuum propagation within the alias-free domain",
    "excluded_scope": "turbulence, nonlinearity",
    "target_observables": ["topological_charge"],
}


def make_services(tmp_path):
    from stov_scientist.artifacts.local_store import LocalStore
    from stov_scientist.artifacts.registry import ArtifactRegistry
    from stov_scientist.campaign.manager import CampaignManager
    from stov_scientist.evidence.claims import ClaimLedger
    from stov_scientist.evidence.ledger import EvidenceLedger
    from stov_scientist.simulation import SimulationRunner, default_solver_registry

    artifacts = ArtifactRegistry(LocalStore(tmp_path / "artifacts"), workdir=tmp_path)
    hypotheses = {
        "hypotheses": [
            {
                "statement": "The STOV topological charge is preserved in vacuum propagation.",
                "claim_type": "BEHAVIOUR",
                "assumptions": ["linear field"],
                "boundary_conditions": ["vacuum"],
                "predictions": ["topological_charge: constant"],
                "falsification_conditions": ["charge changes beyond tolerance"],
                "unknowns": [],
                "testability": "HIGH",
                "evidence_coverage": "UNASSESSED",
                "assumption_burden": "LOW",
                "experimental_feasibility": "MEDIUM",
                "computational_feasibility": "HIGH",
            },
            {
                "statement": "The vortex is a grid artifact, not physical.",
                "claim_type": "BEHAVIOUR",
                "assumptions": [],
                "boundary_conditions": [],
                "predictions": ["topological_charge: grid-dependent"],
                "falsification_conditions": ["charge converges under refinement"],
                "unknowns": [],
                "testability": "HIGH",
                "evidence_coverage": "UNASSESSED",
                "assumption_burden": "LOW",
                "experimental_feasibility": "MEDIUM",
                "computational_feasibility": "HIGH",
            },
        ],
        "rationale": "r",
    }
    mechanisms = {
        "mechanisms": [
            {
                "description": "Phase singularity in (x,t) with winding conserved in linear propagation.",
                "governing_principles": ["phase winding topology"],
                "physical_processes": ["vortex phase"],
                "mechanistic_links": [],
                "assumptions": ["linear"],
                "boundary_conditions": ["vacuum"],
                "predicted_observables": ["topological_charge"],
                "model_requirements": ["FFT grid"],
            }
        ],
        "alternative_notes": "",
    }
    claims = {
        "claims": [
            {
                "statement": "The STOV charge is preserved within the alias-free domain (scope: vacuum, linear).",
                "assumptions": ["linear"],
                "limitations": ["paraxial envelope model"],
            }
        ]
    }
    return ServiceBundle(
        main_model=scripted_model(
            ("Problem", hypotheses),
            ("Hypothesis", mechanisms),
            ("Research content", claims),
        ),
        fast_model=scripted_model(
            (
                "Formalize",
                {
                    "title": PROBLEM_PAYLOAD["title"],
                    "system_under_study": PROBLEM_PAYLOAD["system_under_study"],
                    "scope": PROBLEM_PAYLOAD["scope"],
                    "excluded_scope": PROBLEM_PAYLOAD["excluded_scope"],
                    "target_observables": ["topological_charge"],
                    "known_constraints": [],
                    "unknowns": [],
                },
            )
        ),
        simulation=SimulationRunner(default_solver_registry(), artifacts),
        artifacts=artifacts,
        evidence=EvidenceLedger(),
        claims=ClaimLedger(),
        campaigns=CampaignManager(tmp_path / "campaigns", workdir=tmp_path),
        workdir=tmp_path,
        extra={"literature_clients": {"openalex": FakeLiteratureClient()}},
    )


def invoke_start(graph, services, thread_id="thread-e2e"):
    return graph.invoke(
        {"messages": [HumanMessage(content=json.dumps(PROBLEM_PAYLOAD))]},
        config={"configurable": {"services": services, "thread_id": thread_id}},
    )


def resume(graph, services, thread_id, decision):
    return graph.invoke(
        Command(resume=decision),
        config={"configurable": {"services": services, "thread_id": thread_id}},
    )


def active_gate(result) -> dict:
    """Extract the active interrupt payload from the returned state."""
    interrupts = result.get("__interrupt__") or []
    assert interrupts, "expected a human-gate interrupt in the graph state"
    return interrupts[0].value


def test_e2e_happy_path_with_three_gates(tmp_path):
    from stov_scientist.control.research_graph import graph_with_memory

    services = make_services(tmp_path)
    graph = graph_with_memory(services)

    # 1. intake -> Gate 1 interrupt
    result = invoke_start(graph, services)
    assert active_gate(result)["gate"] == "SCOPE"

    # 2. approve scope -> ... -> Gate 2 interrupt
    result = resume(graph, services, "thread-e2e", {"decision": "APPROVE", "rationale": "scope ok"})
    assert active_gate(result)["gate"] == "HYPOTHESIS_DIRECTION"

    # 3. approve hypotheses -> ... -> Gate 3 interrupt
    result = resume(
        graph,
        services,
        "thread-e2e",
        {"decision": "APPROVE", "rationale": "direction ok"},
    )
    gate3 = active_gate(result)
    assert gate3["gate"] == "FINAL_CLAIM"
    # the scientific objects are presented to the human
    assert "claims" in gate3["object"]
    assert "judgements" in gate3["object"]

    # 4. approve final claims -> audit bundle -> END
    result = resume(
        graph, services, "thread-e2e",
        {"decision": "APPROVE", "rationale": "claims acceptable"},
    )
    assert result["stop_reason"] in ("COMPLETED", "INCONCLUSIVE")
    # audit bundle written on disk
    audit_dir = tmp_path / "campaigns" / "campaign-e2e" / "audit"
    assert (audit_dir / "audit_report.md").exists()
    assert (audit_dir / "research_problem.json").exists()
    assert (audit_dir / "human_decisions.json").exists()
    # pipeline status covers the whole chain
    stages = set(result["pipeline_status"])
    assert {"research_intake", "hypothesis_generation", "scientific_judge", "audit_bundle"} <= stages


def test_e2e_scope_rejection_stops_pipeline(tmp_path):
    from stov_scientist.control.research_graph import graph_with_memory

    services = make_services(tmp_path)
    graph = graph_with_memory(services)
    result = invoke_start(graph, services, thread_id="thread-reject")
    assert active_gate(result)["gate"] == "SCOPE"
    result = resume(
        graph, services, "thread-reject",
        {"decision": "REJECT", "rationale": "scope too narrow"},
    )
    assert result["stop_reason"] == "REJECTED"
    assert result["pipeline_status"]["scope_gate"] == "REJECTED"


def test_e2e_hypothesis_rejection_stops_pipeline(tmp_path):
    from stov_scientist.control.research_graph import graph_with_memory

    services = make_services(tmp_path)
    graph = graph_with_memory(services)
    result = invoke_start(graph, services, thread_id="thread-hreject")
    assert active_gate(result)["gate"] == "SCOPE"
    result = resume(
        graph, services, "thread-hreject", {"decision": "APPROVE", "rationale": "ok"}
    )
    assert active_gate(result)["gate"] == "HYPOTHESIS_DIRECTION"
    result = resume(
        graph, services, "thread-hreject",
        {"decision": "REJECT", "rationale": "wrong direction"},
    )
    assert result["stop_reason"] == "REJECTED"
    assert result["pipeline_status"]["hypothesis_gate"] == "REJECTED"


def test_e2e_no_llm_fallback_pipeline_still_completes(tmp_path):
    """Without any LLM the pipeline uses deterministic templates and still
    reaches a final state (honest INCONCLUSIVE/INSUFFICIENT_EVIDENCE)."""
    from stov_scientist.control.research_graph import graph_with_memory

    services = make_services(tmp_path)
    services.main_model = None
    services.fast_model = None
    graph = graph_with_memory(services)

    result = invoke_start(graph, services, thread_id="thread-nollm")
    assert active_gate(result)["gate"] == "SCOPE"
    result = resume(graph, services, "thread-nollm", {"decision": "APPROVE", "rationale": "ok"})
    assert active_gate(result)["gate"] == "HYPOTHESIS_DIRECTION"
    result = resume(graph, services, "thread-nollm", {"decision": "APPROVE", "rationale": "ok"})
    assert active_gate(result)["gate"] == "FINAL_CLAIM"
    result = resume(graph, services, "thread-nollm", {"decision": "APPROVE", "rationale": "ok"})
    assert result["stop_reason"] in ("COMPLETED", "INCONCLUSIVE")
    # template hypotheses were used and flagged in warnings
    assert any("fallback" in w for w in result.get("warnings", []))


def test_audit_bundle_contains_all_files(tmp_path):
    from stov_scientist.control.research_graph import graph_with_memory

    services = make_services(tmp_path)
    graph = graph_with_memory(services)
    result = invoke_start(graph, services, thread_id="thread-audit")
    assert active_gate(result)["gate"] == "SCOPE"
    result = resume(graph, services, "thread-audit", {"decision": "APPROVE", "rationale": "ok"})
    assert active_gate(result)["gate"] == "HYPOTHESIS_DIRECTION"
    result = resume(graph, services, "thread-audit", {"decision": "APPROVE", "rationale": "ok"})
    assert active_gate(result)["gate"] == "FINAL_CLAIM"
    result = resume(graph, services, "thread-audit", {"decision": "APPROVE", "rationale": "ok"})
    campaign_id = result["campaign_id"]
    audit_dir = tmp_path / "campaigns" / campaign_id / "audit"
    expected = {
        "research_problem.json",
        "ontology.json",
        "search_boundary.json",
        "evidence_ledger.jsonl",
        "hypotheses.json",
        "mechanisms.json",
        "model_spec.json",
        "validation_report.json",
        "simulation_specs.json",
        "simulation_runs.json",
        "counterexamples.json",
        "claims.json",
        "scientific_judgement.json",
        "human_decisions.json",
        "artifact_manifest.json",
        "environment.json",
        "git_status.json",
        "audit_report.md",
    }
    present = {p.name for p in audit_dir.iterdir()}
    assert expected <= present
