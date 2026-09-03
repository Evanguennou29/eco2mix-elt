"""HTTP client for the ODRE Opendatasoft Explore v2.1 API.

Handles pagination (limit/offset over `results`), a request timeout, and
exponential backoff retry on transient errors (429 and 5xx). No API key is
required — the ODRE Explore API is public.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from eco2mix.config import Config

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OdreApiError(RuntimeError):
    """Raised when the ODRE API returns a non-retryable error or retries are exhausted."""


class OdreClient:
    def __init__(self, config: Config, session: requests.Session | None = None) -> None:
        self._config = config
        self._session = session or requests.Session()

    def fetch_records(
        self, dataset_id: str, *, where: str, fields: Sequence[str]
    ) -> Iterator[dict]:
        """Yield every record matching `where`, paginating until a short page is seen."""
        limit = self._config.page_size
        select = ",".join(fields)
        offset = 0
        while True:
            payload = self._get_page(
                dataset_id, where=where, select=select, limit=limit, offset=offset
            )
            results = payload.get("results", [])
            yield from results
            if len(results) < limit:
                return
            offset += limit

    def _get_page(
        self, dataset_id: str, *, where: str, select: str, limit: int, offset: int
    ) -> dict:
        url = f"{self._config.api_base_url}/catalog/datasets/{dataset_id}/records"
        params = {"where": where, "select": select, "limit": limit, "offset": offset}

        last_error: Exception | None = None
        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self._session.get(
                    url, params=params, timeout=self._config.request_timeout_seconds
                )
            except requests.exceptions.Timeout as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    raise OdreApiError(
                        f"ODRE API returned {response.status_code} for {dataset_id} "
                        f"(not retried): {response.text}"
                    )
                last_error = OdreApiError(
                    f"ODRE API returned {response.status_code} for {dataset_id}"
                )

            if attempt < attempts - 1:
                time.sleep(self._config.retry_backoff_base_seconds * (2**attempt))

        raise OdreApiError(
            f"ODRE API request for {dataset_id} failed after {attempts} attempts"
        ) from last_error
