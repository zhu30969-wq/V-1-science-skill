# BUILD_REPORT.md — STOV AI Scientist

All statuses below come from ACTUAL execution output on this machine
(Windows 11, 2026-08-13). Nothing here is fabricated; blocked items are
marked explicitly.

## Repository baseline

| Field | Value |
|---|---|
| Upstream repository | K-Dense-AI/scientific-agent-skills |
| Upstream SHA | `5ad4aae76bc40257b914367afacc6fd686a282d5` |
| Upstream version | 2.63.0 |
| Import method | per-file GitHub API import (network prevented full git fetch; content verbatim; SHA from GitHub API) |
| Branch | `main` (baseline + merge), `feat/stov-ai-scientist` (development) |
| Pushed to origin | YES — both branches |

## Files added / modified

- Upstream content: preserved verbatim (161 skills, tests, docs, workflows,
  LICENSE.md, plugin.json, root pyproject). Collisions kept side-by-side:
  `docs/UPSTREAM_README.md`, `docs/UPSTREAM_CLAUDE.md`, merged `.gitignore`
  with upstream section marked.
- STOV additions: `platform/` (89 source files), `skills/stov-*` (10 skills),
  `web/` (Next.js static export), `gateway/` (Hono Worker), `campaigns/`,
  `artifacts/`, `evals/`, `scripts/`, `.github/workflows/ci.yml` +
  `deploy-pages.yml`, root docs (CLAUDE/ARCHITECTURE/DECISIONS/README).

## Component status (all from real runs)

| Component | Status |
|---|---|
| STOV Skills (10, SKILL.md + references + scripts-with-tests) | PASS |
| Pydantic Contracts (14 schema modules) | PASS |
| LangChain / LangGraph (1.2.11) | PASS |
| Deep Agents (deepagents 0.7.5; worker layer with langgraph fallback) | PASS |
| DeepSeek Runtime | NO_CREDENTIAL (code complete; `platform/.env.example`; lazy models) |
| Evidence System (ledger + claims + provenance) | PASS |
| Physics Validators (10 deterministic validators + ordered runner) | PASS |
| Simulation Harness (4 solvers, registry, selector, convergence) | PASS |
| Contradiction Graph (6-type classification + bounded routing) | PASS |
| Scientific Judge (deterministic rubric, no PROVEN) | PASS |

## Test results (actual)

```
pytest: 151 passed in ~11s   (includes E2E with 3 human gates + B01-B10)
ruff:   All checks passed
mypy:   Success: no issues found in 89 source files
gateway: 6/6 vitest tests PASS, tsc --noEmit PASS
web:    npm run lint PASS, npm run build PASS (static export, out/index.html)
```

## Smoke tests

- `python scripts/smoke_test.py` (direct mode): **PASS** — graph compiled,
  campaign created, research_intake executed, SCOPE human gate reached.
- `langgraph dev` server: CLI 0.4.31 installed and reports version; the
  in-memory dev server additionally requires `langgraph-cli[inmem]`
  (provides `langgraph-api`). That extra install was declined during the
  session — the dev-server E2E remains UNVERIFIED and is one command away:
  `cd platform && uv add --dev "langgraph-cli[inmem]" && uv run --all-groups langgraph dev`.

## Science findings recorded during build (real physics, not bugs)

1. The linear STOV ansatz (x + i·c₀t)·Gaussian splits into a +1/−1 vortex
   pair under vacuum propagation unless the spatiotemporal envelope is
   isotropic (c₀·wt = wx) — measured directly by the platform's singularity
   detector and documented in the model validity domain.
2. Without a carrier frequency, the envelope is baseband and all spatial
   structure is evanescent — propagation now requires `carrier_omega`
   (= 2πc/λ) in the SimulationSpec.
3. Wrapped-phase winding fails for |l| ≥ 2 and near branch cuts; the
   platform uses the complex ratio method (argument principle) instead.
4. Wrapped-phase gradients poison OAM moment integrals; the CANDIDATE_MODEL
   OAM moment now uses complex-ratio phase derivatives.

## Known limitations

- LangSmith tracing: NOT_CONFIGURED (no LANGSMITH_API_KEY).
- LangGraph in-memory dev server: needs `langgraph-cli[inmem]` (see above).
- Subharmonic augmentation of phase screens: documented in the skill but
  not implemented (base FFT method with variance normalization).
- DATA_DRIVEN / HYBRID model routes: NOT_IMPLEMENTED (spec §40) — routed
  to the implemented subset with a warning, never faked.
- OAM moment normalization: CANDIDATE_MODEL (Bliokh & Nori 2012 source
  noted; not validated).
- Literature clients: real OpenAlex/Crossref/arXiv code + tests with
  injected clients; live-network calls not run in this session (no
  `@pytest.mark.network` run).

## NOT_IMPLEMENTED / BLOCKED_BY_CREDENTIAL

| Item | Status |
|---|---|
| Backend deployment (LangSmith cloud) | BLOCKED_BY_CREDENTIAL (no LANGSMITH_API_KEY) — code READY |
| Gateway deployment (Cloudflare) | BLOCKED_BY_CREDENTIAL (no account credentials) — code READY |
| GitHub Pages deployment | READY — workflow committed; first deploy requires enabling Pages source = GitHub Actions (see docs/DEPLOYMENT.md); PUBLIC_GATEWAY_URL variable needs setting |
| LangSmith evaluation datasets | NOT_CONFIGURED (no API key) |
| langgraph dev in-memory server run | BLOCKED on `langgraph-cli[inmem]` install (declined in session) |

## Exact run commands (as executed)

```bash
cd platform
uv sync                                   # OK (120 packages)
uv run pytest -q                          # 151 passed
uv run ruff check .                       # All checks passed
uv run mypy src/stov_scientist            # Success, 89 files
python ../scripts/smoke_test.py           # PASS (direct mode)
cd ../gateway && npm install && npm run build && npm test   # 6/6 PASS
cd ../web && npm install && npm run lint && npm run build    # PASS
git push origin main                      # OK
git push origin feat/stov-ai-scientist    # OK
```

## Deployment URLs

- Live Frontend URL: not yet deployed (Pages source not yet enabled on the
  repository — see docs/DEPLOYMENT.md, one-time manual step).
- Live Gateway URL: none (BLOCKED_BY_CREDENTIAL).
- Live Backend URL: none (BLOCKED_BY_CREDENTIAL).
- Repository: https://github.com/zhu30969-wq/V-1-science-skill

## Next recommended task

1. `cd platform && uv add --dev "langgraph-cli[inmem]"` then
   `uv run --all-groups langgraph dev` — verify the dev server + a real
   streamed run through all three human gates.
2. Enable GitHub Pages (Settings → Pages → Source → GitHub Actions) and
   set the `PUBLIC_GATEWAY_URL` Actions variable once the gateway exists.
3. Provide DEEPSEEK_API_KEY in `platform/.env` and run the `-m llm` suite
   against the real model; then a real campaign in `campaigns/`.
