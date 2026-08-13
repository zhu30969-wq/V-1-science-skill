"""Crossref client — https://api.crossref.org/works (spec PHASE 9)."""

from __future__ import annotations

import httpx

from stov_scientist.errors import LiteratureRetrievalError
from stov_scientist.literature.base import BaseLiteratureClient, ClientResponse, LiteratureRecord
from stov_scientist.schemas import RetrievalStatus


class CrossrefClient(BaseLiteratureClient):
    name = "crossref"
    base_url = "https://api.crossref.org"

    def search(self, query: str, max_results: int = 10) -> ClientResponse:
        try:
            data = self._get_json(
                f"{self.base_url}/works",
                params={
                    "query": query,
                    "rows": min(max_results, 100),
                    "mailto": "stov@scientist.local",
                },
            )
        except httpx.HTTPError as exc:
            raise LiteratureRetrievalError(f"crossref search failed: {exc}") from exc
        except ValueError as exc:
            raise LiteratureRetrievalError(f"crossref returned non-JSON: {exc}") from exc

        records: list[LiteratureRecord] = []
        for item in data.get("message", {}).get("items", []):
            title = (item.get("title") or [""])[0]
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in item.get("author", [])
            ]
            year = None
            for date_key in ("published-print", "published-online", "issued"):
                parts = (item.get(date_key) or {}).get("date-parts") or [[]]
                if parts and parts[0]:
                    year = int(parts[0][0])
                    break
            records.append(
                LiteratureRecord(
                    title=title,
                    authors=authors,
                    year=year,
                    doi=item.get("DOI"),
                    abstract="",
                    venue=((item.get("container-title") or [""])[0]),
                    source_database="crossref",
                    raw=item,
                )
            )
        return ClientResponse(
            status=RetrievalStatus.COMPLETE,
            records=records,
            total_hits=data.get("message", {}).get("total-results"),
        )
