"use client";

import type { SimulationItem } from "@/lib/types";

export default function SimulationCard({ runs }: { runs: SimulationItem[] }) {
  if (!runs.length) {
    return (
      <section className="card">
        <h2>Simulations</h2>
        <p className="muted">No simulation runs recorded.</p>
      </section>
    );
  }
  return (
    <section className="card">
      <h2>Simulations</h2>
      {runs.map((run) => (
        <div key={run.run_id} className="sim-block">
          <div className="sim-row">
            <b>{run.run_id}</b>
            <span className={`sim-status sim-${run.status.toLowerCase()}`}>{run.status}</span>
          </div>
          <div className="sim-meta">
            <span>solver: {run.solver_version || "—"}</span>
            <span>seed: {run.random_seed ?? "—"}</span>
            <span>
              convergence:{" "}
              {run.convergence_result?.achieved === true
                ? "CONVERGED"
                : run.convergence_result?.achieved === false
                  ? "NOT_CONVERGED"
                  : "NOT_RUN"}
            </span>
          </div>
          {run.warnings.length > 0 && (
            <ul className="warn-list">
              {run.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
          {run.errors.length > 0 && (
            <ul className="err-list">
              {run.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <p className="gate-note">
        Numerical failures are recorded as numerical outcomes — they are never
        presented as physical contradictions.
      </p>
    </section>
  );
}
