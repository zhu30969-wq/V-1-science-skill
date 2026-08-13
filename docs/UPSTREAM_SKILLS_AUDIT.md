# UPSTREAM_SKILLS_AUDIT.md — K-Dense skills audit (2026-08-13)

Audited via GitHub API against `K-Dense-AI/scientific-agent-skills@main`
(SHA `5ad4aae76bc40257b914367afacc6fd686a282d5`).

## Repository structure

```
.github/            AGENTS.md   CLAUDE.md   CODE_OF_CONDUCT.md
CONTRIBUTING.md     LICENSE.md  README.md   SECURITY.md
plugin.json         pyproject.toml
scan_pr_skills.py   scan_skills.py
docs/               skills/ (161 skills)    tests/
```

## Spec-referenced skills — ALL PRESENT

| Skill | Used by | Status |
|---|---|---|
| literature-review | Literature Worker | ✅ present upstream — REUSED |
| research-lookup | Literature Worker | ✅ present upstream — REUSED |
| citation-management | Literature Worker | ✅ present upstream — REUSED |
| hypothesis-generation | Hypothesis Worker | ✅ present upstream — REUSED |
| scientific-brainstorming | Hypothesis / Mechanism / Synthesis Workers | ✅ present upstream — REUSED |
| sympy | Mechanism Worker | ✅ present upstream — REUSED |

STOV-specific capabilities are provided by the 10 new `stov-*` skills
(spec PHASE 5); nothing upstream is rewritten or replaced.

## Local modifications policy

Upstream root files are preserved verbatim. Files that collide with STOV
project files are kept alongside:
- upstream README.md content → `docs/UPSTREAM_README.md`
- upstream CLAUDE.md content → `docs/UPSTREAM_CLAUDE.md`

MIT license (LICENSE.md) preserved at root, verbatim.
