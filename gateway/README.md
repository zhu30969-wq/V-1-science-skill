# STOV AI Scientist Gateway

Secure browser/backend boundary (spec PHASE 17):

```
GitHub Pages  ->  Gateway  ->  LangSmith Agent Server  ->  STOV Scientist  ->  DeepSeek
```

## What the gateway guarantees

- The browser NEVER sees `DEEPSEEK_API_KEY` or `LANGSMITH_API_KEY`.
- Backend auth is injected server-side (`x-api-key`).
- CORS allows EXACT origins only — never `*` (spec §61).
- Streaming responses pass through unchanged (graph streams, SSE/NDJSON).
- Basic rate limiting, security headers, error normalization (JSON 502/429/503).

## Secrets

| Secret | Where | Never in |
|---|---|---|
| `LANGGRAPH_API_URL` | gateway env / `wrangler secret put` | GitHub, Pages, `NEXT_PUBLIC_*` |
| `LANGGRAPH_API_KEY` | gateway env / `wrangler secret put` | GitHub, Pages, `NEXT_PUBLIC_*` |

The browser only knows `NEXT_PUBLIC_GATEWAY_URL` (public endpoint).

## Local dev

```bash
npm install
copy .dev.vars.example .dev.vars   # fill LANGGRAPH_API_URL (default http://127.0.0.1:2024)
npm run dev                        # http://127.0.0.1:8787
```

## Tests + build

```bash
npm test        # vitest with mock upstream (offline)
npm run build   # tsc --noEmit typecheck
```

## Deploy (Cloudflare Workers)

```bash
copy wrangler.toml.example wrangler.toml
wrangler secret put LANGGRAPH_API_URL
wrangler secret put LANGGRAPH_API_KEY
wrangler deploy
```

Status without credentials: `GATEWAY_READY` / `BLOCKED_BY_CREDENTIAL`.
