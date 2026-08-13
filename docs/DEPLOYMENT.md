# DEPLOYMENT.md — STOV AI Scientist

Deployment order is strict (spec §24): **Backend → Gateway → Pages**.

## 1. Backend (LangSmith / LangGraph)

```bash
cd platform
copy .env.example .env          # DEEPSEEK_API_KEY (+ LANGSMITH_* for tracing)
uv sync
uv run pytest -q                # must PASS before any deploy
uv run ruff check . && uv run mypy src/stov_scientist
uv run langgraph dev            # local validation (server starts, graph
                                # imports, assistant exists, test run starts)
uv run langgraph deploy         # current official cloud deployment
```

Record the real `LANGGRAPH_API_URL` from the deployment output.
Status: `BACKEND_DEPLOYED` only after a real API smoke test succeeds;
otherwise `BACKEND_READY` / `BLOCKED_BY_CREDENTIAL`.

## 2. Gateway (Cloudflare Workers)

```bash
cd gateway
npm install && npm test && npm run build
copy wrangler.toml.example wrangler.toml
wrangler secret put LANGGRAPH_API_URL   # real backend URL
wrangler secret put LANGGRAPH_API_KEY   # real LangSmith key
wrangler deploy
```

Record the real `PUBLIC_GATEWAY_URL`. Browser-compatible streaming smoke
test required before `GATEWAY_DEPLOYED`.

## 3. GitHub Pages

**One-time setup** (only if the Pages source was not already set
programmatically):

> Repository → Settings → Pages → Build and deployment → Source →
> **GitHub Actions**

Then set the repository variable (NOT a secret — it is public):

> Repository → Settings → Secrets and variables → Actions → Variables →
> `PUBLIC_GATEWAY_URL` = the deployed gateway URL

Push to `main` → `.github/workflows/deploy-pages.yml` builds `web/out`
(with `NEXT_PUBLIC_BASE_PATH=/V-1-science-skill`) and deploys to
`https://zhu30969-wq.github.io/V-1-science-skill/`.

Status: `PAGES_DEPLOYED` only after the Actions deployment succeeds.

## Local E2E (3 terminals)

```bash
cd platform && uv run langgraph dev                    # T1
cd gateway && npm run dev                              # T2 (after npm install + .dev.vars)
cd web && npm run dev                                  # T3 (after npm install + .env.local)
```

Smoke: `python scripts/smoke_test.py` (direct) or
`python scripts/smoke_test.py --server http://127.0.0.1:2024`.

## Secrets matrix

| Secret | Lives in | NEVER in |
|---|---|---|
| DEEPSEEK_API_KEY | platform/.env (local) / LangGraph platform | git, Pages, NEXT_PUBLIC_* |
| LANGSMITH_API_KEY | platform/.env / gateway secrets | git, Pages, NEXT_PUBLIC_* |
| LANGGRAPH_API_URL | gateway secrets | git, Pages, NEXT_PUBLIC_* |
| PUBLIC_GATEWAY_URL | GitHub Actions variable (public) | — |
