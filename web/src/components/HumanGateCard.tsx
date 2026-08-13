"use client";

import { useState } from "react";
import type { GateDecision, GatePayload } from "@/lib/types";

export default function HumanGateCard({
  gate,
  busy,
  onResume,
}: {
  gate: GatePayload;
  busy: boolean;
  onResume: (decision: GateDecision) => void;
}) {
  const [rationale, setRationale] = useState("");
  const [edit, setEdit] = useState("");

  const decide = (decision: "APPROVE" | "EDIT" | "REJECT") => {
    const payload: GateDecision = {
      decision,
      rationale: rationale || "(human decision from web console)",
    };
    if (decision === "EDIT" && edit.trim()) {
      try {
        const parsed = JSON.parse(edit);
        if (gate.gate === "SCOPE") payload.edited_problem = parsed;
        if (gate.gate === "HYPOTHESIS_DIRECTION") payload.edited_hypotheses = parsed;
        if (gate.gate === "FINAL_CLAIM") payload.edited_claims = parsed;
      } catch {
        payload.rationale = `${payload.rationale} [EDIT payload was not valid JSON and was ignored]`;
      }
    }
    onResume(payload);
  };

  return (
    <section className="card gate-card">
      <h2 className="gate-title">⚠ Review Required</h2>
      <p className="gate-subtitle">{gate.title}</p>
      <details>
        <summary>Scientific object (JSON)</summary>
        <pre className="gate-json">{JSON.stringify(gate.object, null, 2)}</pre>
      </details>
      <textarea
        className="input"
        placeholder="Rationale (recorded in the audit bundle)"
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
      />
      <textarea
        className="input"
        placeholder="EDIT only: JSON replacement object (optional)"
        value={edit}
        onChange={(e) => setEdit(e.target.value)}
      />
      <div className="gate-buttons">
        <button className="btn btn-approve" disabled={busy} onClick={() => decide("APPROVE")}>
          Approve
        </button>
        <button className="btn btn-edit" disabled={busy} onClick={() => decide("EDIT")}>
          Edit
        </button>
        <button className="btn btn-reject" disabled={busy} onClick={() => decide("REJECT")}>
          Reject
        </button>
      </div>
      <p className="gate-note">
        These buttons send a real LangGraph <code>Command(resume=...)</code> to
        the agent server — not a frontend fake state.
      </p>
    </section>
  );
}
