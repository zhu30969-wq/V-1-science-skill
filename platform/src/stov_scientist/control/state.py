"""ResearchState (spec §37): lightweight — IDs only, never large data.

PDFs, NumPy arrays, fields, phase screens, videos, full texts and large
DataFrames are FORBIDDEN here. They live behind Artifact IDs.
"""

from __future__ import annotations

from langgraph.graph import MessagesState


class ResearchState(MessagesState, total=False):
    # identity
    campaign_id: str
    thread_id: str

    # problem / ontology / evidence
    research_problem_id: str
    ontology_id: str
    evidence_set_id: str
    search_boundary_id: str

    # hypotheses
    hypothesis_set_id: str
    selected_hypothesis_ids: list[str]

    # mechanisms / model
    mechanism_set_id: str
    model_spec_id: str
    model_route: str  # ANALYTICAL / NUMERICAL / DATA_DRIVEN / HYBRID
    validation_report_id: str
    model_revision_count: int
    max_model_revisions: int
    max_research_iterations: int
    # validation subgraph channels
    validation_passed: bool
    validation_action: str
    validation_message: str

    # simulation
    simulation_spec_id: str
    simulation_run_ids: list[str]
    simulation_retry_count: int
    max_simulation_retries: int
    # simulation subgraph channels (names shared with SimulationGraphState)
    solver_valid: bool
    run_status: str
    retry_count: int
    max_retries: int
    completed: bool
    message: str
    contradiction_id: str
    contradiction_kind: str
    contradiction_action: str

    # counterexamples / contradictions
    counterexample_set_id: str
    contradiction_ids: list[str]

    # claims / judgement
    claim_bundle_id: str
    judgement_ids: list[str]

    # audit
    audit_bundle_id: str

    # loop control (spec §43) — bounded by AcceptancePolicy
    current_stage: str
    iteration: int
    gate_status: str  # NONE / WAITING_SCOPE / WAITING_HYPOTHESIS / WAITING_FINAL / HUMAN_REVIEW_REQUIRED
    stop_reason: str  # COMPLETED / INCONCLUSIVE / LIMIT_REACHED / REJECTED / ERROR

    # small status payloads (scalars/strings only)
    pipeline_status: dict[str, str]
    warnings: list[str]
