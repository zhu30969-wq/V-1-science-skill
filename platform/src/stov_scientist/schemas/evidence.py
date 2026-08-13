"""EvidenceRecord — literature/external evidence with provenance (spec §9, §36)."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from stov_scientist.schemas.common import (
    ID,
    BaseRecord,
    EvidenceQuality,
    EvidenceRelation,
    Identifiers,
    ProvenanceRecord,
    SearchBoundary,
    SourceType,
    utcnow,
)


class EvidenceRecord(BaseRecord):
    evidence_id: ID
    source_type: SourceType
    source_id: str = Field(description="identifier within its source, e.g. OpenAlex W-ID")
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    identifiers: Identifiers = Field(default_factory=Identifiers)
    claim_ids: list[ID] = Field(default_factory=list)
    relation: EvidenceRelation = EvidenceRelation.UNKNOWN
    summary: str = ""
    retrieval_date: datetime = Field(default_factory=utcnow)
    search_boundary_id: ID | None = None
    provenance: ProvenanceRecord = Field(default_factory=ProvenanceRecord)
    evidence_quality: EvidenceQuality = EvidenceQuality.UNASSESSED
    quality_reason: str = ""

    @property
    def normalized_doi(self) -> str | None:
        from stov_scientist.schemas.common import normalize_doi

        return normalize_doi(self.identifiers.doi)


class EvidenceSet(BaseRecord):
    """A named, search-boundary-scoped collection of evidence records."""

    evidence_set_id: ID
    campaign_id: ID
    search_boundaries: list[SearchBoundary] = Field(default_factory=list)
    records: list[EvidenceRecord] = Field(default_factory=list)

    def by_relation(self, relation: EvidenceRelation) -> list[EvidenceRecord]:
        return [r for r in self.records if r.relation is relation]
