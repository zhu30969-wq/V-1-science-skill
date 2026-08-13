/** Shared frontend types mirroring the platform schemas (lightweight). */

export type PipelineStageName =
  | "research_intake"
  | "scope_gate"
  | "problem_formalization"
  | "initial_ontology"
  | "literature_research"
  | "evidence_extraction"
  | "ontology_refinement"
  | "gap_analysis"
  | "hypothesis_generation"
  | "rival_generation"
  | "prediction_derivation"
  | "hypothesis_gate"
  | "mechanism_exploration"
  | "model_route_selector"
  | "model_assembly"
  | "validation_graph"
  | "model_gate"
  | "simulation_planning"
  | "solver_selection"
  | "simulation_graph"
  | "observable_extraction"
  | "counterexample_search"
  | "contradiction_evaluation"
  | "evidence_update"
  | "claim_synthesis"
  | "scientific_judge"
  | "final_claim_gate"
  | "audit_bundle";

export type StageStatus =
  | "PENDING"
  | "RUNNING"
  | "WAITING_FOR_HUMAN"
  | "PASSED"
  | "FAILED"
  | "INCONCLUSIVE"
  | "COMPLETED";

export interface PipelineStatus {
  [stage: string]: string;
}

export type ResearchState = {
  campaign_id?: string;
  current_stage?: string;
  pipeline_status?: PipelineStatus;
  gate_status?: string;
  stop_reason?: string;
  warnings?: string[];
  validation_report_id?: string;
  simulation_run_ids?: string[];
  claim_bundle_id?: string;
  audit_bundle_id?: string;
} & Record<string, unknown>;

export interface GatePayload {
  gate: "SCOPE" | "HYPOTHESIS_DIRECTION" | "FINAL_CLAIM";
  title: string;
  object: unknown;
  options: string[];
}

export interface GateDecision {
  decision: "APPROVE" | "EDIT" | "REJECT";
  rationale: string;
  selected_hypothesis_ids?: string[];
  edited_problem?: Record<string, unknown>;
  edited_hypotheses?: unknown[];
  edited_claims?: unknown[];
}

export interface EvidenceItem {
  evidence_id: string;
  source_type: string;
  title: string;
  authors: string[];
  year?: number | null;
  identifiers?: { doi?: string | null };
  relation: string;
  search_boundary_id?: string | null;
  quality?: string;
}

export interface ModelItem {
  model_id: string;
  name: string;
  equations: { equation_id: string; symbolic_form: string; status: string }[];
  symbols: Record<string, string>;
  convention_ids: string[];
  validity_domain?: { description: string };
  validation_status?: string;
}

export interface SimulationItem {
  run_id: string;
  simulation_spec_id: string;
  status: string;
  solver_version: string;
  random_seed?: number | null;
  convergence_result?: { achieved?: boolean | null; deviation?: number | null };
  warnings: string[];
  errors: string[];
}
