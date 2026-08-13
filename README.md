# STOV AI Scientist

AI research scientist platform for **Space-Time Optical Vortex (STOV)** science —
optical engineering, atmospheric propagation, theoretical modeling, scientific
simulation, hypothesis verification and counterexample search.

Built on **Scientific Agent Skills + LangChain + LangGraph + Deep Agents +
DeepSeek API**.

> This project EXTENDS [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
> (MIT License, attribution preserved — see [docs/UPSTREAM_BASELINE.md](docs/UPSTREAM_BASELINE.md)).

## Overview

STOV AI Scientist is a **scientific control plane**, not a chatbot:

```
Research Question → Problem Formalization → Ontology → Literature → Evidence
→ Hypotheses → Rival Hypotheses → Predictions → Human Gate → Mechanisms
→ Scientific Model → Physics Validation → Simulation → Numerical Validation
→ Counterexample → Contradiction Classification → Evidence Update
→ Scientific Judge → Human Final Review → Audit Bundle
```

## Architecture

| Layer | Role |
|---|---|
| **LangGraph** | Scientific Control Plane — routing, human gates, bounded loops |
| **Deep Agents** | bounded long-horizon research workers |
| **Scientific Skills** | K-Dense upstream skills + 10 `stov-*` domain skills |
| **Pydantic** | scientific contracts (`platform/src/stov_scientist/schemas/`) |
| **SymPy / Pint / NumPy / SciPy** | deterministic validation + compute |
| **LangSmith** | tracing + evaluation + deployment |
| **GitHub Pages** | static web frontend only |
| **Gateway** | secure browser/backend boundary (secret holder) |
| **DeepSeek** | LLM provider (`DEEPSEEK_API_KEY` only) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full Mermaid diagrams.

## Scientific Integrity (enforced, not aspirational)

- LLM output ≠ scientific evidence; Hypothesis ≠ Evidence; Model ≠
  Hypothesis; Simulation ≠ Experiment.
- Simulation disagreement ≠ hypothesis falsification; numerical failure ≠
  physical contradiction; "not found in search" ≠ "no literature exists".
- Hypotheses are never ranked as truth probabilities. Status vocabulary:
  CANDIDATE / SUPPORTED_WITHIN_SCOPE / PARTIALLY_SUPPORTED / INCONCLUSIVE /
  CONTRADICTED / INSUFFICIENT_EVIDENCE. **INCONCLUSIVE is a valid outcome.**
- Every claim carries provenance: Claim → Evidence → Model → Simulation →
  Parameters → Code → Git Commit → Environment.
- Every STOV equation needs a source chain (primary source → reference →
  convention → transcription → unit/dim check → limiting case → unit test);
  otherwise it is CANDIDATE_MODEL, never a validated model.
- All loops are bounded by the campaign AcceptancePolicy; no unbounded
  autonomous research loops; no secrets in source control.

## Technology Stack

- **Python 3.12 + uv** — `platform/` (independent package)
- **LangChain / LangGraph 1.x / Deep Agents / langchain-deepseek**
- **DeepSeek models** — `deepseek-v4-pro` (main: reasoning/hypothesis/
  mechanism) and `deepseek-v4-flash` (fast: extraction/classification)
- **Next.js (static export) + TypeScript + @langchain/react +
  @langchain/langgraph-sdk** — `web/`
- **Hono (Cloudflare Worker compatible)** — `gateway/`
- **GitHub Actions** — CI + GitHub Pages deployment

## Claude Code + DeepSeek development note

The development environment may itself connect to DeepSeek via
`ANTHROPIC_*`; that is irrelevant to the runtime. The STOV Python runtime
uses **DEEPSEEK_API_KEY only** — see `platform/.env.example`.

## Backend Runtime

```bash
cd platform
copy .env.example .env      # fill DEEPSEEK_API_KEY (optional for offline tests)
uv sync                     # installs everything + lockfile
uv run pytest -q            # full deterministic suite (offline)
uv run ruff check .
uv run mypy src/stov_scientist
```

## STOV Skills

10 domain skills under `skills/`: `stov-optical-conventions`,
`stov-field-modeling`, `stov-topology-analysis`, `stov-observables`,
`stov-wave-propagation`, `stov-atmospheric-turbulence`,
`stov-phase-screen-simulation`, `stov-optical-sampling`,
`stov-numerical-convergence`, `stov-model-validation`.
Each has `SKILL.md` + `references/`; scripts come with tests.

## LangGraph Workflow

31-node ResearchGraph (see ARCHITECTURE.md) with:

- **3 Human Gates** — SCOPE / HYPOTHESIS_DIRECTION / FINAL_CLAIM via
  LangGraph `interrupt()`; the web console sends real `Command(resume=...)`.
- **ValidationGraph** — ordered deterministic validators.
- **SimulationGraph** — bounded retries (sampling redesign / numerical fix).
- **ContradictionGraph** — classification per spec §45 with loop limits.

## Deep Agents

Bounded workers with isolated skill sets (spec §33):

| Worker | Skills |
|---|---|
| literature | literature-review, research-lookup, citation-management |
| hypothesis | hypothesis-generation, scientific-brainstorming |
| mechanism | sympy, scientific-brainstorming, stov-optical-conventions, stov-field-modeling, stov-wave-propagation |
| counterexample | stov-model-validation, stov-topology-analysis, stov-numerical-convergence |
| synthesis | scientific-brainstorming |

Structured output → Pydantic; one retry, then STRUCTURED_OUTPUT_FAILURE.

## Scientific Validation

Schema → Units (Pint) → Dimensions → Symbols (SymPy) → Limits → Boundary →
Topology → Sampling → Physics. Deterministic first, LLM last.

## Simulation

SolverRegistry + SolverSelector (NO_VALID_SOLVER when nothing fits):
`angular_spectrum_xt` / `angular_spectrum_xy` / `fresnel_xy` /
`split_step_xt`. Convergence against campaign AcceptancePolicy rules —
no universal thresholds. Turbulence via TurbulenceModelRegistry
(von Kármán / Tatarskii, Andrews & Phillips 2005).

## Evidence

OpenAlex / Crossref / arXiv clients with timeout/retry/backoff,
multi-key dedup (DOI → title → year + author overlap), documented
SearchBoundary per search, PARTIAL_RETRIEVAL on network failure.

## Web

Research-console UI: pipeline graph with real node status, streaming worker
activity, Human Gate cards, evidence table, model/simulation cards, audit
view. All state comes from the real graph stream.

## GitHub Pages

`https://zhu30969-wq.github.io/V-1-science-skill/` — static export
(`output: "export"`, `basePath: /V-1-science-skill`, `trailingSlash: true`).
Deployed by `.github/workflows/deploy-pages.yml`.

## Gateway

`gateway/` — Hono reverse proxy (Cloudflare Worker compatible): server-side
auth injection, exact-origin CORS, streaming pass-through, rate limiting,
security headers, error normalization. See `gateway/README.md`.

## LangSmith Deployment

```bash
cd platform
uv run langgraph dev          # local agent server (http://127.0.0.1:2024)
uv run langgraph deploy       # cloud deployment (requires credentials)
```

Tracing is enabled when `LANGSMITH_API_KEY` is present; everything runs
locally without it.

## Local Development (3 terminals)

```bash
# T1: backend
cd platform && uv run langgraph dev
# T2: gateway
cd gateway && npm install && copy .dev.vars.example .dev.vars && npm run dev
# T3: frontend
cd web && npm install && echo NEXT_PUBLIC_GATEWAY_URL=http://127.0.0.1:8787 > .env.local && npm run dev
```

Full local E2E: Browser → Gateway → Agent Server → LangGraph → Deep Agent →
DeepSeek, including all three Human Gates.

## Tests

```bash
cd platform && uv run pytest -q      # deterministic suite (no LLM, no network)
uv run pytest -q -m llm              # real-LLM tests (skipped without key)
cd gateway && npm test
cd web && npm run lint && npm run build
```

STOV benchmark B01–B10 in `platform/tests/benchmark/` (also declared in
`evals/benchmark/`).

## Research Campaign

Campaigns live in `campaigns/<campaign_id>/` with a full audit bundle
(`audit/`): research_problem, ontology, search_boundary, evidence_ledger,
hypotheses, mechanisms, model_spec, validation_report, simulation_specs,
simulation_runs, counterexamples, claims, scientific_judgement,
human_decisions, artifact_manifest, environment, git_status, audit_report.md.

## Limitations

See BUILD_REPORT.md — includes NOT_IMPLEMENTED items (e.g. DATA_DRIVEN /
HYBRID model routes, subharmonic phase-screen augmentation, OAM moment
normalization as CANDIDATE_MODEL) and everything BLOCKED_BY_CREDENTIAL.

## Upstream Project

Base: [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
— see [docs/UPSTREAM_BASELINE.md](docs/UPSTREAM_BASELINE.md) and
[docs/UPSTREAM_SYNC.md](docs/UPSTREAM_SYNC.md).

## License

MIT (upstream K-Dense attribution preserved).
