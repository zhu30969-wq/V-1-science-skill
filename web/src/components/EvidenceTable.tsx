"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/lib/types";

export default function EvidenceTable({ items }: { items: EvidenceItem[] }) {
  const [filter, setFilter] = useState<"ALL" | "SUPPORT" | "CONTRADICT" | "CONTEXT">(
    "ALL"
  );
  const filtered =
    filter === "ALL" ? items : items.filter((e) => e.relation === filter);

  if (!items.length) {
    return (
      <section className="card">
        <h2>Evidence</h2>
        <p className="muted">
          No evidence records yet. Retrieval outcomes are scoped by a
          documented SearchBoundary — &ldquo;not found&rdquo; never means
          &ldquo;nobody has studied this&rdquo;.
        </p>
      </section>
    );
  }
  return (
    <section className="card">
      <h2>Evidence</h2>
      <div className="filters">
        {(["ALL", "SUPPORT", "CONTRADICT", "CONTEXT"] as const).map((f) => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? "filter-active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>
      <table className="evidence-table">
        <thead>
          <tr>
            <th>Source</th>
            <th>Authors</th>
            <th>Year</th>
            <th>DOI</th>
            <th>Relation</th>
            <th>Search Boundary</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((e) => (
            <tr key={e.evidence_id}>
              <td>{e.title}</td>
              <td>{(e.authors || []).join(", ")}</td>
              <td>{e.year ?? "—"}</td>
              <td>{e.identifiers?.doi ?? "—"}</td>
              <td>
                <span className={`rel rel-${e.relation.toLowerCase()}`}>{e.relation}</span>
              </td>
              <td>{e.search_boundary_id ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
