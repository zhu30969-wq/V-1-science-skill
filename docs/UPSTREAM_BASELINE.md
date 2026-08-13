# UPSTREAM_BASELINE.md — Upstream import record (spec PHASE 1)

| Field | Value |
|---|---|
| Upstream repository | https://github.com/K-Dense-AI/scientific-agent-skills |
| Upstream commit SHA | `5ad4aae76bc40257b914367afacc6fd686a282d5` |
| Upstream commit date | 2026-08-12T00:44:32Z |
| Upstream commit message | "Update documentation and versioning for Agent Plugins compliance" |
| Scientific Agent Skills version | 2.63.0 (per upstream README / pyproject at that commit) |
| Import date | 2026-08-13 |
| Import method | upstream/main snapshot (git fetch --depth=1; SHA verified via GitHub API) |
| License | MIT (upstream LICENSE preserved verbatim) |

## Local modifications policy

1. Upstream `skills/`, `tests/`, `docs/`, `plugin.json`, `LICENSE` and
   upstream README scientific content are PRESERVED — never bulk-deleted.
2. STOV work EXTENDS the upstream tree: `platform/` (independent Python
   package — upstream root pyproject untouched), `skills/stov-*` domain
   skills, `web/`, `gateway/`, `campaigns/`, `artifacts/`, `evals/`,
   `scripts/`, `.github/workflows/`, and the root documentation set.
3. Attribution: upstream README content and MIT license remain; STOV
   additions are documented in README.md ("Upstream Project" section).
4. Upstream sync is manual and tested — see docs/UPSTREAM_SYNC.md.
