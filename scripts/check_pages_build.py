#!/usr/bin/env python3
"""Verify the GitHub Pages static export (spec §78): web/out/index.html,
assets, and basePath correctness."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "web" / "out"
BASE_PATH = "/V-1-science-skill"


def main() -> int:
    failures: list[str] = []

    if not (OUT_DIR / "index.html").exists():
        failures.append("web/out/index.html missing — run `npm run build` in web/")

    if not (OUT_DIR / "_next").exists():
        failures.append("web/out/_next missing — static assets not exported")

    if (OUT_DIR / "index.html").exists():
        html = (OUT_DIR / "index.html").read_text(encoding="utf-8")
        # assets must be referenced under the basePath for GitHub Pages
        asset_refs = re.findall(r'(?:src|href)="([^"]*_next[^"]*)"', html)
        if asset_refs and not any(ref.startswith(BASE_PATH) for ref in asset_refs):
            failures.append(
                f"assets not under basePath {BASE_PATH}: {asset_refs[:2]}... "
                "(was NEXT_PUBLIC_BASE_PATH set during the build?)"
            )

    # local-dev builds (no basePath) are legitimate; only flag when the
    # Pages build is intended. Report what we see.
    if failures:
        print("PAGES_BUILD_CHECK: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("PAGES_BUILD_CHECK: PASS")
    print(f"  index.html: {'OK' if (OUT_DIR / 'index.html').exists() else 'missing'}")
    print(f"  assets dir: {'OK' if (OUT_DIR / '_next').exists() else 'missing'}")
    if (OUT_DIR / "index.html").exists():
        html = (OUT_DIR / "index.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:src|href)="([^"]*_next[^"]*)"', html)
        prefix = refs[0].split("/_next")[0] if refs else "(no _next refs)"
        print(f"  asset prefix: {prefix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
