"""ScientificArtifact (spec §16)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from stov_scientist.schemas.common import ID, BaseRecord, utcnow


class ScientificArtifact(BaseRecord):
    artifact_id: ID
    campaign_id: ID
    artifact_type: str = Field(
        description="e.g. FIELD_NPY / FIELD_NC / PHASE_SCREEN / FIGURE_PNG / "
        "VALIDATION_REPORT / MODEL_SPEC / EVIDENCE_JSONL"
    )
    path_or_uri: str
    created_by: str = "stov-ai-scientist"
    created_at: datetime = Field(default_factory=utcnow)
    source_ids: list[ID] = Field(default_factory=list)
    git_commit: str = ""
    working_tree_dirty: bool | None = None
    environment_hash: str = ""
    code_hash: str = ""
    random_seed: int | None = None
    parameters: dict = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)
    sha256: str = Field(description="SHA256 of the payload file (hex)")
    metadata: dict = Field(default_factory=dict)
