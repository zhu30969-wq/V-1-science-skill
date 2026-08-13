"""Evidence Ledger (spec §18): SQLite-backed store with JSONL export.

Relations: Claim <-> Evidence via SUPPORT / CONTRADICT / CONTEXT / UNKNOWN
(relation lives on the EvidenceRecord's claim_ids + relation field).

v1 storage: SQLite metadata + JSON/JSONL artifacts (no Neo4j).
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from stov_scientist.errors import EvidenceError
from stov_scientist.schemas import EvidenceRecord, EvidenceRelation, EvidenceSet, SearchBoundary


class Base(DeclarativeBase):
    pass


class EvidenceRow(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evidence_set_id: Mapped[str] = mapped_column(String(128), index=True)
    search_boundary_id: Mapped[str] = mapped_column(String(128), default="")
    title: Mapped[str] = mapped_column(Text)
    authors: Mapped[str] = mapped_column(Text, default="[]")
    year: Mapped[int | None] = mapped_column(default=None)
    doi: Mapped[str] = mapped_column(String(256), default="")
    source_type: Mapped[str] = mapped_column(String(32), default="OTHER")
    relation: Mapped[str] = mapped_column(String(16), default="UNKNOWN")
    quality: Mapped[str] = mapped_column(String(16), default="UNASSESSED")
    record_json: Mapped[str] = mapped_column(Text)


class BoundaryRow(Base):
    __tablename__ = "search_boundaries"

    search_boundary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    record_json: Mapped[str] = mapped_column(Text)


class EvidenceLedger:
    def __init__(self, database_url: str = "") -> None:
        if database_url:
            self.engine: Engine = create_engine(database_url)
        else:
            self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    # -- search boundaries ---------------------------------------------------
    def add_boundary(self, boundary: SearchBoundary) -> None:
        with Session(self.engine) as session:
            session.merge(
                BoundaryRow(
                    search_boundary_id=boundary.search_boundary_id,
                    record_json=boundary.model_dump_json(),
                )
            )
            session.commit()

    def get_boundary(self, boundary_id: str) -> SearchBoundary | None:
        with Session(self.engine) as session:
            row = session.get(BoundaryRow, boundary_id)
        return SearchBoundary.model_validate_json(row.record_json) if row else None

    # -- records --------------------------------------------------------------
    def add_record(self, record: EvidenceRecord, evidence_set_id: str) -> None:
        with Session(self.engine) as session:
            session.merge(
                EvidenceRow(
                    evidence_id=record.evidence_id,
                    evidence_set_id=evidence_set_id,
                    search_boundary_id=record.search_boundary_id or "",
                    title=record.title,
                    authors=json.dumps(record.authors),
                    year=record.year,
                    doi=record.normalized_doi or "",
                    source_type=record.source_type.value,
                    relation=record.relation.value,
                    quality=record.evidence_quality.value,
                    record_json=record.model_dump_json(),
                )
            )
            session.commit()

    def get_record(self, evidence_id: str) -> EvidenceRecord | None:
        with Session(self.engine) as session:
            row = session.get(EvidenceRow, evidence_id)
        return EvidenceRecord.model_validate_json(row.record_json) if row else None

    def list_records(
        self,
        evidence_set_id: str | None = None,
        relation: EvidenceRelation | None = None,
    ) -> list[EvidenceRecord]:
        stmt = select(EvidenceRow)
        if evidence_set_id:
            stmt = stmt.where(EvidenceRow.evidence_set_id == evidence_set_id)
        if relation:
            stmt = stmt.where(EvidenceRow.relation == relation.value)
        with Session(self.engine) as session:
            rows = session.execute(stmt).scalars().all()
        return [EvidenceRecord.model_validate_json(r.record_json) for r in rows]

    def export_jsonl(self, path: Path, evidence_set_id: str | None = None) -> int:
        """Append-style JSONL export; returns the number of records written."""
        records = self.list_records(evidence_set_id)
        with path.open("a", encoding="utf-8") as fh:
            for record in records:
                fh.write(record.model_dump_json() + "\n")
        return len(records)

    def to_evidence_set(self, evidence_set_id: str) -> EvidenceSet:
        boundaries = [
            b
            for r in self.list_records(evidence_set_id)
            if (b := self.get_boundary(r.search_boundary_id or "")) is not None
        ]
        # dedupe boundaries by id
        unique: dict[str, SearchBoundary] = {b.search_boundary_id: b for b in boundaries}
        return EvidenceSet(
            evidence_set_id=evidence_set_id,
            campaign_id=evidence_set_id.split("::")[0],
            search_boundaries=list(unique.values()),
            records=self.list_records(evidence_set_id),
        )


def merge_evidence_sets(sets: list[EvidenceSet], evidence_set_id: str, campaign_id: str) -> EvidenceSet:
    """Merge evidence sets with cross-set dedup handled by the caller (spec
    §35: dedup happens in the literature layer, not here)."""
    seen: set[str] = set()
    records = []
    boundaries: dict[str, SearchBoundary] = {}
    for es in sets:
        for b in es.search_boundaries:
            boundaries.setdefault(b.search_boundary_id, b)
        for r in es.records:
            if r.evidence_id not in seen:
                seen.add(r.evidence_id)
                records.append(r)
    if not records and not boundaries:
        raise EvidenceError("cannot merge empty evidence sets")
    return EvidenceSet(
        evidence_set_id=evidence_set_id,
        campaign_id=campaign_id,
        search_boundaries=list(boundaries.values()),
        records=records,
    )
