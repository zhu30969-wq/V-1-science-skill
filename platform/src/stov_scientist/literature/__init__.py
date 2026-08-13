"""Literature research layer (spec PHASE 9)."""

from stov_scientist.literature.base import ClientResponse, LiteratureRecord
from stov_scientist.literature.dedup import deduplicate, same_paper
from stov_scientist.literature.search import SearchOutcome, search_literature

__all__ = [
    "ClientResponse",
    "LiteratureRecord",
    "SearchOutcome",
    "deduplicate",
    "same_paper",
    "search_literature",
]
