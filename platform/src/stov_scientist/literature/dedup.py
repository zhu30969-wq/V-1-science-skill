"""Literature deduplication (spec §35).

Keys: normalized DOI, then title, then year + author overlap. Never
title equality alone.
"""

from __future__ import annotations

from stov_scientist.literature.base import LiteratureRecord, _normalize_title
from stov_scientist.schemas.common import normalize_doi


def _author_tokens(name: str) -> frozenset[str]:
    """Token-set author normalization: 'Chong, A.' and 'A. Chong' both
    reduce to {a, chong} (punctuation stripped, order-insensitive)."""
    import re

    tokens = re.findall(r"[a-z0-9]+", name.lower())
    return frozenset(tokens)


def author_overlap(a: list[str], b: list[str]) -> float:
    """Jaccard-like overlap of token-set-normalized author name sets."""
    sa = {_author_tokens(n) for n in a if n.strip()}
    sb = {_author_tokens(n) for n in b if n.strip()}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa), len(sb))


def same_paper(r1: LiteratureRecord, r2: LiteratureRecord) -> bool:
    doi1, doi2 = normalize_doi(r1.doi), normalize_doi(r2.doi)
    if doi1 and doi2:
        return doi1 == doi2
    if doi1 or doi2:
        return False  # one has a DOI, the other does not: do not conflate
    if r1.openalex_id and r2.openalex_id:
        return r1.openalex_id == r2.openalex_id
    if r1.arxiv_id and r2.arxiv_id:
        return r1.arxiv_id == r2.arxiv_id
    if _normalize_title(r1.title) != _normalize_title(r2.title):
        return False
    if r1.year and r2.year and r1.year != r2.year:
        return False
    return author_overlap(r1.authors, r2.authors) >= 0.5


def deduplicate(records: list[LiteratureRecord]) -> list[LiteratureRecord]:
    """Return unique records (first occurrence wins), preserving order."""
    unique: list[LiteratureRecord] = []
    for record in records:
        if not any(same_paper(record, seen) for seen in unique):
            unique.append(record)
    return unique
