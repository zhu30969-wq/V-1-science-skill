"""LiteratureSearchService: multi-database search inside a SearchBoundary.

Produces EvidenceSet + SearchBoundary bookkeeping. Partial retrieval is
explicit — "not found" only means "not located within the documented search
boundary" (spec §19).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

from stov_scientist.literature.base import ClientResponse, LiteratureRecord, search_or_partial
from stov_scientist.literature.crossref_client import CrossrefClient
from stov_scientist.literature.dedup import deduplicate
from stov_scientist.literature.openalex_client import OpenAlexClient
from stov_scientist.schemas import (
    EvidenceRecord,
    EvidenceRelation,
    EvidenceSet,
    Identifiers,
    ProvenanceRecord,
    RetrievalStatus,
    SearchBoundary,
    SourceType,
    utcnow,
)


@dataclass
class SearchOutcome:
    evidence_set: EvidenceSet | None
    boundary: SearchBoundary
    retrieval_errors: list[str] = field(default_factory=list)

    @property
    def fully_retrieved(self) -> bool:
        return self.boundary.retrieval_status is RetrievalStatus.COMPLETE and not self.retrieval_errors


def _build_clients(databases: list[str], **kwargs) -> dict[str, object]:
    clients: dict[str, object] = {}
    for db in databases:
        if db == "openalex":
            clients[db] = OpenAlexClient(**kwargs)
        elif db == "crossref":
            clients[db] = CrossrefClient(**kwargs)
        elif db == "arxiv":
            from stov_scientist.literature.arxiv_client import ArxivClient

            clients[db] = ArxivClient(**kwargs)
        else:
            raise ValueError(f"unknown database {db!r}")
    return clients


def search_literature(
    queries: list[str],
    databases: list[str],
    *,
    campaign_id: str,
    evidence_set_id: str,
    boundary_id: str,
    max_per_query: int = 10,
    client_kwargs: dict | None = None,
    clients: dict[str, object] | None = None,
) -> SearchOutcome:
    """Run every query against every requested database, deduplicate, and
    build EvidenceSet + SearchBoundary in one deterministic pass.

    ``clients``: injected database-name -> client objects (tests / offline);
    when omitted, real OpenAlex/Crossref/arXiv clients are built.
    """
    kwargs = client_kwargs or {}
    resolved = clients if clients is not None else _build_clients(databases, **kwargs)
    raw: list[LiteratureRecord] = []
    errors: list[str] = []

    try:
        for query in queries:
            for db, client in resolved.items():
                try:
                    response: ClientResponse = search_or_partial(
                        cast(Any, client), query, max_results=max_per_query
                    )
                finally:
                    pass
                if response.status is RetrievalStatus.PARTIAL_RETRIEVAL:
                    errors.extend(
                        [f"{db} ({query!r}): {e}" for e in response.errors]
                    )
                raw.extend(response.records)
    finally:
        for client in resolved.values():
            close = getattr(client, "close", None)
            if close:
                close()

    deduped = deduplicate(raw)
    boundary = SearchBoundary(
        search_boundary_id=boundary_id,
        databases=databases,
        queries=queries,
        retrieved_count=len(raw),
        deduplicated_count=len(deduped),
        limitations=[
            f"search limited to databases: {', '.join(databases)}",
            f"max {max_per_query} results per query per database",
        ],
        retrieval_status=(
            RetrievalStatus.PARTIAL_RETRIEVAL if errors else RetrievalStatus.COMPLETE
        ),
    )

    records = [
        _to_evidence(r, boundary_id, evidence_set_id, index=i + 1)
        for i, r in enumerate(deduped)
    ]
    return SearchOutcome(
        evidence_set=EvidenceSet(
            evidence_set_id=evidence_set_id,
            campaign_id=campaign_id,
            search_boundaries=[boundary],
            records=records,
        ),
        boundary=boundary,
        retrieval_errors=errors,
    )


def _to_evidence(
    record: LiteratureRecord, boundary_id: str, evidence_set_id: str, index: int
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=f"{evidence_set_id}-{index:04d}",
        source_type=_source_type(record),
        source_id=(
            record.openalex_id
            or record.arxiv_id
            or record.doi
            or record.identifier_key()
        ),
        title=record.title,
        authors=record.authors,
        year=record.year,
        identifiers=Identifiers(
            doi=record.doi,
            arxiv=record.arxiv_id,
            openalex=record.openalex_id,
        ),
        relation=EvidenceRelation.CONTEXT,
        summary=record.abstract[:2000],
        retrieval_date=utcnow(),
        search_boundary_id=boundary_id,
        provenance=ProvenanceRecord(
            source_ids=[f"db-{record.source_database}"],
        ),
    )


def _source_type(record: LiteratureRecord) -> SourceType:
    if record.source_database == "arxiv":
        return SourceType.PREPRINT
    return SourceType.JOURNAL
