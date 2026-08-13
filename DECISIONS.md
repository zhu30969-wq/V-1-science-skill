# DECISIONS.md — Architecture Decision Records

## ADR-001 — LangGraph is the Scientific Control Plane

Deep Agents never decide the scientific workflow. LangGraph owns routing,
gates, loops and stop conditions; Deep Agents are invoked as bounded
workers with isolated skill sets.

## ADR-002 — Deep Agents are bounded long-horizon workers

Only literature research, mechanism exploration, counterexample search and
synthesis go to Deep Agents. Everything else is deterministic or
sub-second LLM calls inside graph nodes.

## ADR-003 — Pydantic contracts between agents and core

Every agent-to-agent and agent-to-core payload is a Pydantic schema
(`platform/src/stov_scientist/schemas/`). Free-text Markdown is never the
inter-agent protocol; structured-output failure retries exactly once then
STRUCTURED_OUTPUT_FAILURE.

## ADR-004 — Artifact references in State, never data

ResearchState holds IDs only. Fields, phase screens, arrays, PDFs and
DataFrames live in the artifact store (SHA256 + metadata in SQLite) and are
referenced by artifact_id.

## ADR-005 — No automated truth ranking

Hypotheses may carry qualitative transparency axes (testability, evidence
coverage, assumption burden, feasibility) but never automatic probabilities
like "H1 = 92%". Selection passes through the Human Gate or explicit
SELECTED_FOR_TEST. Status vocabulary has no PROVEN/TRUE.

## ADR-006 — Deterministic validation first

Validation order: Pydantic → Pint → SymPy → NumPy/SciPy → LLM (last
resort). The Scientific Judge is a deterministic code evaluator
(`evidence/judge.py`), not an LLM-as-judge.

## ADR-007 — DeepSeek via langchain-deepseek

The runtime uses DEEPSEEK_API_KEY only (main: deepseek-v4-pro; fast:
deepseek-v4-flash) via a single model factory (`config/models.py`).
Model names never appear in agent code.

## ADR-008 — GitHub Pages is a static frontend

Next.js `output: "export"`, `trailingSlash: true`, basePath
`/V-1-science-skill` on Pages builds; no Server Actions / API routes / SSR
runtime. Local dev keeps basePath empty.

## ADR-009 — Gateway protects backend secrets

A Cloudflare-Worker-compatible Hono proxy holds LANGGRAPH_API_URL and
LANGGRAPH_API_KEY server-side, injects auth, enforces exact-origin CORS
(never `*`), rate limits and streams responses. The browser only knows
NEXT_PUBLIC_GATEWAY_URL.

## ADR-010 — LangSmith is the preferred backend deployment

LangGraph deployment via the current official CLI (`langgraph dev` /
`langgraph deploy`). Without credentials the system must still run locally
and is marked BLOCKED_BY_CREDENTIAL, never faked as DEPLOYED.

## ADR-011 — Single turbulence model is forbidden

`TurbulenceModelRegistry` holds von Kármán / Tatarskii (Andrews & Phillips
2005) with per-model parameter validation. Every screen records model id +
parameters + seed.

## ADR-012 — Convergence thresholds come from AcceptancePolicy

No universal 0.90 / 95% / 1e-6 thresholds anywhere. Campaign
`ConvergenceRule`s define metric, target and min refinements; the judge
reads the resulting ConvergenceResult.
