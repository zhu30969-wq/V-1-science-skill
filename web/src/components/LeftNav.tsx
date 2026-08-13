"use client";

const ITEMS = [
  { id: "new-research", label: "New Research" },
  { id: "campaigns", label: "Campaigns" },
  { id: "evidence", label: "Evidence" },
  { id: "hypotheses", label: "Hypotheses" },
  { id: "models", label: "Models" },
  { id: "simulations", label: "Simulations" },
  { id: "artifacts", label: "Artifacts" },
  { id: "audit", label: "Audit" },
];

export default function LeftNav({
  active,
  onSelect,
}: {
  active: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="leftnav">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          className={`nav-item ${active === item.id ? "nav-item-active" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          {item.label}
        </button>
      ))}
      <div className="leftnav-footnote">
        LangGraph scientific control plane
        <br />
        Deep Agents = bounded workers
      </div>
    </nav>
  );
}
