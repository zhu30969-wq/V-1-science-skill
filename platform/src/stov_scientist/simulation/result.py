"""SimulationRun assembly + persistence (spec §15, §16)."""

from __future__ import annotations

from pathlib import Path

import orjson

from stov_scientist.artifacts.hashing import git_commit, git_dirty
from stov_scientist.artifacts.registry import ArtifactRegistry
from stov_scientist.schemas import SimulationRun, utcnow


def persist_run(
    run: SimulationRun,
    registry: ArtifactRegistry,
    campaign_id: str,
    workdir: Path | None = None,
) -> str:
    """Write the run record as an audit artifact; returns its artifact id."""
    record = run.model_copy(
        update={
            "git_commit": git_commit(workdir),
            "working_tree_dirty": git_dirty(workdir),
            "runtime_metadata": {
                **(run.runtime_metadata.model_dump()),
                "finished_at": utcnow(),
            },
        }
    )
    payload = orjson.dumps(record.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
    registry.register_artifact(
        campaign_id=campaign_id,
        artifact_type="SIMULATION_RUN",
        artifact_id=f"simrun-{run.run_id}",
        payload=payload,
        random_seed=run.random_seed,
        parameters={},
    )
    return f"simrun-{run.run_id}"
