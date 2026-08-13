"""arXiv client — https://export.arxiv.org/api/query (Atom feed)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx

from stov_scientist.errors import LiteratureRetrievalError
from stov_scientist.literature.base import BaseLiteratureClient, ClientResponse, LiteratureRecord
from stov_scientist.schemas import RetrievalStatus

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivClient(BaseLiteratureClient):
    name = "arxiv"
    base_url = "https://export.arxiv.org/api/query"

    def _get_feed(self, query: str, max_results: int) -> str:
        self._throttle()
        try:
            response = self._client.get(
                self.base_url,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": min(max_results, 50),
                },
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise LiteratureRetrievalError(f"arxiv search failed: {exc}") from exc

    def search(self, query: str, max_results: int = 10) -> ClientResponse:
        try:
            feed = self._get_feed(query, max_results)
        except LiteratureRetrievalError:
            raise
        except Exception as exc:
            raise LiteratureRetrievalError(f"arxiv fetch error: {exc}") from exc

        try:
            root = ET.fromstring(feed)
        except ET.ParseError as exc:
            raise LiteratureRetrievalError(f"arxiv returned invalid Atom XML: {exc}") from exc

        records: list[LiteratureRecord] = []
        for entry in root.findall("atom:entry", _NS):
            title = " ".join(
                (entry.findtext("atom:title", default="", namespaces=_NS) or "").split()
            )
            authors = [
                (a.findtext("atom:name", default="", namespaces=_NS) or "").strip()
                for a in entry.findall("atom:author", _NS)
            ]
            arxiv_id = (
                entry.findtext("atom:id", default="", namespaces=_NS).split("/abs/")[-1]
            )
            published = entry.findtext("atom:published", default="", namespaces=_NS)
            year = int(published[:4]) if len(published) >= 4 else None
            doi = None
            for link in entry.findall("atom:link", _NS):
                href = link.get("href", "")
                if "doi.org" in href and not href.startswith("http://arxiv"):
                    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", href)
            records.append(
                LiteratureRecord(
                    title=title,
                    authors=authors,
                    year=year,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    abstract=" ".join(
                        (entry.findtext("atom:summary", default="", namespaces=_NS) or "").split()
                    ),
                    venue="arXiv",
                    source_database="arxiv",
                    raw={"published": published},
                )
            )
        return ClientResponse(
            status=RetrievalStatus.COMPLETE,
            records=records,
            total_hits=len(records),
        )
