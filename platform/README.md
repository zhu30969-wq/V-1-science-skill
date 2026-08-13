# STOV Scientist — Python Platform

Scientific control plane for Space-Time Optical Vortex research.
Independent Python package (spec: platform/ must not pollute the upstream
root pyproject).

## Layout

```
platform/
├── pyproject.toml          # dependencies + tool config (uv)
├── langgraph.json          # LangGraph CLI config (graphs.stov_scientist)
├── .env.example            # runtime config template (copy to .env)
├── src/stov_scientist/
│   ├── schemas/            # Pydantic scientific contracts
│   ├── physics/            # conventions, fields, propagation, topology,
│   │                       # observables, turbulence, field builders,
│   │                       # model templates
│   ├── validators/         # deterministic validator chain + runner
│   ├── simulation/         # SolverRegistry, selector, runner, solvers/
│   ├── artifacts/          # registry, local store, hashing
│   ├── evidence/           # ledger, claims, judge, provenance
│   ├── literature/         # OpenAlex / Crossref / arXiv clients + dedup
│   ├── workers/            # bounded Deep Agent research workers
│   ├── control/            # LangGraph research/validation/simulation/
│   │                       # contradiction graphs + routers + services
│   ├── campaign/           # campaign manager + audit bundle
│   ├── config/             # Settings + DeepSeek model factory
│   └── errors.py           # error taxonomy
└── tests/                  # deterministic suite + benchmark B01-B10
```

## Commands

```bash
uv sync                    # install (generates uv.lock)
uv run pytest -q           # deterministic tests (offline)
uv run pytest -q -m llm    # real-LLM tests (skipped without DEEPSEEK_API_KEY)
uv run ruff check .
uv run mypy src/stov_scientist
uv run langgraph dev       # local LangGraph server
python ../scripts/smoke_test.py   # backend smoke test (direct mode)
```

## Notes

- The module-level graph in `control/research_graph.py` builds with lazy
  models — importing it never requires DEEPSEEK_API_KEY.
- Graph state holds IDs only; large data lives in the artifact store.
