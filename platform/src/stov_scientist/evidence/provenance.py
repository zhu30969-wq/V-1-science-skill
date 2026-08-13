"""Provenance capture and completeness checks (spec §36, §49).

environment.json contains: Python version, OS, package versions, DeepSeek
model names, git commit, dirty status, solver versions, random seeds.
NEVER any secret material.
"""

from __future__ import annotations

import importlib.metadata
import platform as _platform
import sys
from pathlib import Path
from typing import Any

from stov_scientist.artifacts.hashing import environment_hash, git_commit, git_dirty
from stov_scientist.schemas import EvidenceRecord, ScientificClaim


def capture_environment(workdir: Path | None = None) -> dict[str, Any]:
    packages = {}
    for name in (
        "numpy",
        "scipy",
        "sympy",
        "pint",
        "langgraph",
        "langchain",
        "deepagents",
        "langchain-deepseek",
        "langsmith",
        "pydantic",
        "stov-scientist",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not-installed"
    return {
        "python_version": _platform.python_version(),
        "python_implementation": _platform.python_implementation(),
        "os": _platform.platform(),
        "packages": packages,
        "git_commit": git_commit(workdir),
        "working_tree_dirty": git_dirty(workdir),
        "environment_hash": environment_hash(),
        "executable": sys.executable,
    }


def evidence_provenance_complete(records: list[EvidenceRecord]) -> tuple[bool, list[str]]:
    """All records carry a search boundary + identifier + retrieval date."""
    problems: list[str] = []
    for r in records:
        if not r.search_boundary_id:
            problems.append(f"{r.evidence_id}: missing search_boundary_id")
        if not (r.identifiers.doi or r.identifiers.arxiv or r.identifiers.openalex):
            problems.append(f"{r.evidence_id}: missing external identifier")
    return (not problems), problems


def claim_provenance_complete(claim: ScientificClaim, records: list[EvidenceRecord]) -> bool:
    """Every evidence id referenced by the claim exists in the record set."""
    known = {r.evidence_id for r in records}
    referenced = set(claim.supporting_evidence_ids) | set(claim.contradicting_evidence_ids)
    return referenced <= known
