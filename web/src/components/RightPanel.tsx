"use client";

import type { ResearchState } from "@/lib/types";
import StatusChip from "./StatusChip";

export default function RightPanel({ state }: { state?: ResearchState }) {
  const warnings = state?.warnings ?? [];
  const stopReason = state?.stop_reason;
  const gateStatus = state?.gate_status;
  return (
    <aside className="rightpanel">
      <section className="card">
        <h2>Current Scientific State</h2>
        <dl className="kv">
          <dt>Stage</dt>
          <dd>{state?.current_stage ?? "—"}</dd>
          <dt>Campaign</dt>
          <dd>{state?.campaign_id ?? "—"}</dd>
          <dt>Stop reason</dt>
          <dd>{stopReason ?? "—"}</dd>
          <dt>Gate</dt>
          <dd>{gateStatus ?? "NONE"}</dd>
        </dl>
      </section>

      <section className="card">
        <h2>Validation</h2>
        <p className="muted">
          {state?.validation_report_id
            ? `Report: ${state.validation_report_id}`
            : "Deterministic validators (schema → units → dimensions → symbols → limits → boundary → sampling) run before any scientific conclusion."}
        </p>
      </section>

      <section className="card">
        <h2>Evidence</h2>
        <p className="muted">
          Every claim requires provenance: Claim → Evidence → Model →
          Simulation → Parameters → Code → Git → Environment.
        </p>
      </section>

      <section className="card">
        <h2>Human Review</h2>
        {gateStatus === "WAITING_SCOPE" && <StatusChip status="WAITING_FOR_HUMAN" />}
        {gateStatus === "HUMAN_REVIEW_REQUIRED" && <StatusChip status="FAILED" />}
        <p className="muted">
          Scope approval, hypothesis/model direction, and final claim approval
          are human gates. INCONCLUSIVE is a valid scientific outcome.
        </p>
      </section>

      <section className="card">
        <h2>Warnings</h2>
        {warnings.length ? (
          <ul className="warn-list">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">none</p>
        )}
      </section>
    </aside>
  );
}
