"""Literature client infrastructure (spec PHASE 9, §35, §36).

Every client: timeout + retry + backoff + rate handling + partial retrieval
status. Network failure -> PARTIAL_RETRIEVAL — NEVER "ZERO_LITERATURE".
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from stov_scientist.errors import LiteratureRetrievalError
from stov_scientist.schemas import RetrievalStatus


@dataclass
class LiteratureRecord:
    """Unified record produced by every literature database client."""

    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openalex_id: str | None = None
    abstract: str = ""
    venue: str = ""
    source_database: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def identifier_key(self) -> str:
        """Stable dedup key (spec §35: normalized DOI preferred)."""
        from stov_scientist.schemas.common import normalize_doi

        doi = normalize_doi(self.doi)
        if doi:
            return f"doi:{doi}"
        if self.openalex_id:
            return f"openalex:{self.openalex_id}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        return f"title:{_normalize_title(self.title)}"


def _normalize_title(title: str) -> str:
    import re

    t = title.strip().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


@dataclass
class ClientResponse:
    status: RetrievalStatus
    records: list[LiteratureRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_hits: int | None = None


class BaseLiteratureClient:
    """Shared transport: timeout, retries, exponential backoff, min-interval
    rate limiting, per-call partial status."""

    name = "base"
    base_url = ""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 2,
        min_interval: float = 0.35,
        user_agent: str = "stov-ai-scientist/0.1 (research platform; mailto:stov@scientist.local)",
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = min_interval
        self.user_agent = user_agent
        self._last_request = 0.0
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        reraise=True,
    )
    def _get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        response = self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def search(self, query: str, max_results: int = 10) -> ClientResponse:
        """Subclasses implement database-specific search.

        Default behaviour on network error: return PARTIAL_RETRIEVAL with the
        errors recorded — the caller must never interpret this as
        ZERO_LITERATURE (spec §36).
        """
        raise NotImplementedError

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BaseLiteratureClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def search_or_partial(
    client: BaseLiteratureClient, query: str, max_results: int
) -> ClientResponse:
    """Execute a search; network errors degrade to PARTIAL_RETRIEVAL."""
    try:
        return client.search(query, max_results=max_results)
    except LiteratureRetrievalError as exc:
        return ClientResponse(status=RetrievalStatus.PARTIAL_RETRIEVAL, errors=[str(exc)])
    except Exception as exc:
        return ClientResponse(
            status=RetrievalStatus.PARTIAL_RETRIEVAL,
            errors=[f"{type(exc).__name__}: {exc}"],
        )
