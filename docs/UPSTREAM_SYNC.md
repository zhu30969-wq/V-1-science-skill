# UPSTREAM_SYNC.md — Upstream sync procedure (spec §82)

No automatic scheduled upstream merges. Manual, reviewed, tested.

```bash
git fetch upstream
git checkout main
git merge upstream/main
# resolve conflicts carefully — NEVER delete upstream skills/tests/docs
# run the complete test suite before pushing:
cd platform && uv run pytest -q
cd ../gateway && npm test
cd ../web && npm run lint && npm run build
git push origin main
```

Rules:

1. Upstream MIT License and attribution must remain intact.
2. Never bulk-delete K-Dense `skills/`, `tests/`, `docs/`, `plugin.json`,
   `LICENSE` or upstream README content.
3. STOV work extends upstream; it does not destroy + rewrite.
4. If the upstream merge conflicts with platform changes, resolve in favour
   of keeping BOTH (upstream content preserved; platform content kept).
