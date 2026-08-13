"""Shared schema primitives: IDs, provenance, enums, source references."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ID_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,127}$"

ID = Annotated[str, StringConstraints(pattern=ID_PATTERN)]


def utcnow() -> datetime:
    return datetime.now(UTC)


class BaseRecord(BaseModel):
    """Common base for all scientific records."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)


# --------------------------------------------------------------------------
# Enums shared across the scientific contract layer
# --------------------------------------------------------------------------


class EvidenceRelation(StrEnum):
    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    CONTEXT = "CONTEXT"
    UNKNOWN = "UNKNOWN"


class EvidenceQuality(StrEnum):
    """Ordinal quality bucket — NOT a numeric probability.

    Spec §9: confidence = 0.937 style pseudo-probabilities are forbidden.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNASSESSED = "UNASSESSED"


class SourceType(StrEnum):
    JOURNAL = "JOURNAL"
    PREPRINT = "PREPRINT"
    BOOK = "BOOK"
    CONFERENCE = "CONFERENCE"
    DATABASE = "DATABASE"
    TEXTBOOK = "TEXTBOOK"
    PRIMARY_EXPERIMENT = "PRIMARY_EXPERIMENT"
    PRIMARY_SIMULATION = "PRIMARY_SIMULATION"
    INTERNAL_NOTE = "INTERNAL_NOTE"
    OTHER = "OTHER"


class EquationStatus(StrEnum):
    """Provenance status of an equation.

    VALIDATED: transcribed from a primary/authoritative source and passed the
               unit/dimension/limiting-case test chain (spec §20).
    CANDIDATE_MODEL: LLM-generated or otherwise unverified — must never be
               treated as a validated physics model.
    """

    VALIDATED = "VALIDATED"
    CANDIDATE_MODEL = "CANDIDATE_MODEL"


class RetrievalStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL_RETRIEVAL = "PARTIAL_RETRIEVAL"
    FAILED = "FAILED"


# --------------------------------------------------------------------------
# Provenance & sources
# --------------------------------------------------------------------------


class SourceRef(BaseRecord):
    """Pointer to the origin of a fact, equation or record.

    All scientific claims must carry provenance (spec principle 10).
    """

    source_id: ID
    kind: SourceType = SourceType.OTHER
    title: str | None = None
    uri: str | None = None
    doi: str | None = None
    accessed_at: datetime | None = None


class ProvenanceRecord(BaseRecord):
    """Creation-time provenance for derived scientific objects."""

    created_by: str = "stov-ai-scientist"
    created_at: datetime = Field(default_factory=utcnow)
    git_commit: str | None = None
    working_tree_dirty: bool | None = None
    code_hash: str | None = None
    source_ids: list[ID] = Field(default_factory=list)


class Identifiers(BaseRecord):
    """External identifiers of a publication."""

    doi: str | None = None
    arxiv: str | None = None
    openalex: str | None = None
    crossref: str | None = None
    isbn: str | None = None
    pmid: str | None = None


def normalize_doi(doi: str | None) -> str | None:
    """Lower-case and strip DOI wrapper (https://doi.org/..., doi: ...)."""
    if not doi:
        return None
    d = doi.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    d = re.sub(r"^doi:\s*", "", d)
    return d or None


class SearchBoundary(BaseRecord):
    """Documented boundary of a literature search (spec §19).

    "Not found" is only ever valid relative to THIS boundary — never
    interpreted as "nobody has studied this".
    """

    search_boundary_id: ID
    search_date: datetime = Field(default_factory=utcnow)
    databases: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    time_range: tuple[int | None, int | None] | None = None  # (from_year, to_year)
    language_scope: list[str] = Field(default_factory=lambda: ["en"])
    retrieved_count: int = 0
    deduplicated_count: int = 0
    limitations: list[str] = Field(default_factory=list)
    retrieval_status: RetrievalStatus = RetrievalStatus.COMPLETE
