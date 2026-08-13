"""OpenAlex client — https://api.openalex.org/works (spec PHASE 9)."""

from __future__ import annotations

from typing import Any

import httpx

from stov_scientist.errors import LiteratureRetrievalError
from stov_scientist.literature.base import BaseLiteratureClient, ClientResponse, LiteratureRecord
from stov_scientist.schemas import RetrievalStatus


class OpenAlexClient(BaseLiteratureClient):
    name = "openalex"
    base_url = "https://api.openalex.org"

    def search(self, query: str, max_results: int = 10) -> ClientResponse:
        try:
            data = self._get_json(
                f"{self.base_url}/works",
                params={
                    "search": query,
                    "per-page": min(max_results, 200),
                    "mailto": "stov@scientist.local",
                },
            )
        except httpx.HTTPError as exc:
            raise LiteratureRetrievalError(f"openalex search failed: {exc}") from exc
        except ValueError as exc:
            raise LiteratureRetrievalError(f"openalex returned non-JSON: {exc}") from exc

        records: list[LiteratureRecord] = []
        for item in data.get("results", []):
            authorships = item.get("authorships") or []
            authors = [a.get("author", {}).get("display_name", "") for a in authorships]
            authors = [a for a in authors if a]
            doi = item.get("doi")
            doi = doi.replace("https://doi.org/", "") if doi else None
            records.append(
                LiteratureRecord(
                    title=(item.get("title") or "").strip(),
                    authors=authors,
                    year=item.get("publication_year"),
                    doi=doi,
                    openalex_id=item.get("id"),
                    abstract="",
                    venue=_primary_location_source(item),
                    source_database="openalex",
                    raw=item,
                )
            )
        return ClientResponse(
            status=RetrievalStatus.COMPLETE,
            records=records,
            total_hits=data.get("meta", {}).get("count"),
        )


def _primary_location_source(item: dict[str, Any]) -> str:
    locations = item.get("primary_location") or {}
    source = locations.get("source") or {}
    return source.get("display_name", "") or ""
