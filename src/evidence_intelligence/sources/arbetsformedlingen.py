from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


DATA_IT_OCCUPATION_FIELD_CONCEPT_ID = "apaJ_2ja_LuF"


def _api_datetime(value: datetime) -> str:
    """Format an aware/naive datetime for JobStream's documented query contract."""
    return value.replace(tzinfo=None).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class JobStreamConfig:
    base_url: str = "https://jobstream.api.jobtechdev.se"
    timeout_seconds: float = 60.0
    user_agent: str = "events-to-evidence-decision-support-data-platform/0.1.0"


class JobStreamClient:
    """Adapter for Arbetsförmedlingen JobStream v2.

    JobStream is the ingestion boundary for the first slice because the provider
    recommends it for keeping a local copy / ingesting a market subset.  The
    client requests NDJSON so records can be processed without loading a large
    response into memory.
    """

    def __init__(
        self,
        config: JobStreamConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or JobStreamConfig()
        self._client = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            headers={
                "Accept": "application/jsonl",
                "User-Agent": self.config.user_agent,
            },
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JobStreamClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def iter_changes(
        self,
        updated_after: datetime,
        *,
        updated_before: datetime | None = None,
        occupation_concept_ids: tuple[str, ...] = (),
        location_concept_ids: tuple[str, ...] = (),
    ) -> Iterator[str]:
        params: list[tuple[str, str]] = [
            ("updated-after", _api_datetime(updated_after)),
        ]
        if updated_before is not None:
            if updated_before <= updated_after:
                raise ValueError("updated_before must be later than updated_after")
            params.append(("updated-before", _api_datetime(updated_before)))

        params.extend(("occupation-concept-id", value) for value in occupation_concept_ids)
        params.extend(("location-concept-id", value) for value in location_concept_ids)

        with self._client.stream("GET", "/v2/stream", params=params) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.strip():
                    yield line


@dataclass(frozen=True, slots=True)
class JobSearchConfig:
    base_url: str = "https://jobsearch.api.jobtechdev.se"
    timeout_seconds: float = 30.0
    user_agent: str = "events-to-evidence-decision-support-data-platform/0.1.0"


class JobSearchClient:
    """Small exploratory adapter for Arbetsförmedlingen JobSearch.

    This remains useful for inspecting a few current ads, but it is deliberately
    *not* the primary ingestion path for the vertical slice.
    """

    def __init__(
        self,
        config: JobSearchConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or JobSearchConfig()
        self._client = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            headers={
                "Accept": "application/json",
                "User-Agent": self.config.user_agent,
            },
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "JobSearchClient":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
        occupation_field: str | None = None,
    ) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query must not be blank")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        params: dict[str, str | int] = {
            "q": query,
            "limit": limit,
            "offset": offset,
        }
        if occupation_field:
            params["occupation-field"] = occupation_field

        response = self._client.get("/search", params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("JobSearch response must be a JSON object")
        return payload

    def get_ad(self, ad_id: str) -> dict[str, Any]:
        ad_id = ad_id.strip()
        if not ad_id:
            raise ValueError("ad_id must not be blank")
        response = self._client.get(f"/ad/{ad_id}")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("JobSearch ad response must be a JSON object")
        return payload
