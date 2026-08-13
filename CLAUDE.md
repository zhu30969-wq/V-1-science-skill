# CLAUDE.md — STOV AI Scientist 长期工程规则

LANGGRAPH IS THE SCIENTIFIC CONTROL PLANE.

DEEP AGENTS ARE BOUNDED WORKERS.

NEVER TREAT LLM OUTPUT AS SCIENTIFIC EVIDENCE.

NEVER FABRICATE LITERATURE.

NEVER RANK HYPOTHESES AS TRUTH PROBABILITIES.

NEVER BYPASS PHYSICS OR NUMERICAL VALIDATION.

NEVER STORE LARGE SIMULATION DATA IN GRAPH STATE.

ALL CLAIMS REQUIRE PROVENANCE.

INCONCLUSIVE IS A VALID SCIENTIFIC OUTCOME.

NO UNBOUNDED AGENT LOOPS.

NO SECRET IN SOURCE CONTROL.

## Working rules

- Backend code lives in `platform/` (independent Python package, Python 3.12, uv).
- Frontend is `web/` (Next.js static export for GitHub Pages) — no Server
  Actions, no API routes, no server runtime.
- `gateway/` is the only party holding backend secrets.
- Every STOV equation needs a source chain (primary source → reference →
  convention → transcription → unit/dim check → limiting case → unit test).
  Without it: CANDIDATE_MODEL.
- Tests: `pytest` (mark real-LLM tests with `@pytest.mark.llm`), `ruff`,
  `mypy src/stov_scientist`, `npm run lint/build` (web), `npm test` (gateway).
- Run commands from `platform/` with `uv run ...`.
- Commit in logical stages; never one giant commit.
- Any step needing credentials that are absent is marked
  `BLOCKED_BY_CREDENTIAL` — never faked as DONE.
