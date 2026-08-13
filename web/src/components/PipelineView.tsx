"use client";

import type { PipelineStageName } from "@/lib/types";
import StatusChip from "./StatusChip";

const STAGES: { id: PipelineStageName; label: string }[] = [
  { id: "research_intake", label: "Problem" },
  { id: "initial_ontology", label: "Ontology" },
  { id: "literature_research", label: "Literature" },
  { id: "evidence_extraction", label: "Evidence" },
  { id: "hypothesis_generation", label: "Hypothesis" },
  { id: "mechanism_exploration", label: "Mechanism" },
  { id: "model_assembly", label: "Model" },
  { id: "validation_graph", label: "Validation" },
  { id: "simulation_graph", label: "Simulation" },
  { id: "counterexample_search", label: "Counterexample" },
  { id: "scientific_judge", label: "Judge" },
  { id: "audit_bundle", label: "Audit" },
];

export default function PipelineView({
  status,
  currentStage,
}: {
  status?: Record<string, string>;
  currentStage?: string;
}) {
  return (
    <div className="pipeline">
      {STAGES.map((stage, i) => {
        const s = status?.[stage.id];
        return (
          <div key={stage.id} className="pipeline-row">
            <div className={`pipe-node ${currentStage === stage.id ? "pipe-active" : ""}`}>
              <span className="pipe-label">{stage.label}</span>
              <StatusChip status={s ?? "PENDING"} />
            </div>
            {i < STAGES.length - 1 && <div className="pipe-edge" />}
          </div>
        );
      })}
    </div>
  );
}
