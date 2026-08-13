"use client";

import type { ModelItem } from "@/lib/types";

export default function ModelCard({ model }: { model: ModelItem | null }) {
  if (!model) {
    return (
      <section className="card">
        <h2>Scientific Model</h2>
        <p className="muted">No model assembled yet.</p>
      </section>
    );
  }
  return (
    <section className="card">
      <h2>Scientific Model — {model.model_id}</h2>
      <h3>Equations</h3>
      <ul className="eq-list">
        {model.equations.map((eq) => (
          <li key={eq.equation_id}>
            <code>{eq.symbolic_form}</code>{" "}
            <span className={`eq-status eq-${eq.status.toLowerCase()}`}>{eq.status}</span>
          </li>
        ))}
      </ul>
      <h3>Symbols &amp; Units</h3>
      <div className="symbol-grid">
        {Object.entries(model.symbols).map(([sym, unit]) => (
          <span key={sym} className="symbol-chip">
            {sym} [{unit}]
          </span>
        ))}
      </div>
      <h3>Conventions</h3>
      <div className="symbol-grid">
        {model.convention_ids.map((c) => (
          <span key={c} className="symbol-chip">
            {c}
          </span>
        ))}
      </div>
      <h3>Validity Domain</h3>
      <p className="muted">{model.validity_domain?.description ?? "—"}</p>
      <h3>Validation Status</h3>
      <p>{model.validation_status ?? "NOT_RUN"}</p>
    </section>
  );
}
