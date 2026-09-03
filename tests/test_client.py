import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from eco2mix.config import Config
from eco2mix.ingest.client import OdreApiError, OdreClient

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "eco2mix-national-tr"


def _config(**overrides) -> Config:
    base = dict(
        api_base_url="https://example.test/api/explore/v2.1",
        request_timeout_seconds=7.0,
        max_retries=2,
        retry_backoff_base_seconds=0.0,
        page_size=2,
        raw_data_dir=Path("unused"),
    )
    base.update(overrides)
    return Config(**base)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def _mock_response(status_code: int, payload: dict | None = None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = json.dumps(payload) if payload is not None else ""
    return response


def test_fetch_records_paginates_across_fixture_pages_until_a_short_page():
    day = _load_fixture("2024-01-01.json")
    all_results = day["results"]
    limit = 2
    pages = [all_results[i : i + limit] for i in range(0, len(all_results), limit)]

    session = MagicMock()
    session.get.side_effect = [
        _mock_response(200, {"total_count": len(all_results), "results": page}) for page in pages
    ]

    client = OdreClient(_config(page_size=limit), session=session)
    records = list(
        client.fetch_records(
            "eco2mix-national-tr", where="date = '2024-01-01'", fields=("date", "heure")
        )
    )

    assert records == all_results
    assert session.get.call_count == len(pages)  # 5 records over pages of 2 -> 3 pages

    first_params = session.get.call_args_list[0].kwargs["params"]
    assert first_params == {
        "where": "date = '2024-01-01'",
        "select": "date,heure",
        "limit": limit,
        "offset": 0,
    }
    second_params = session.get.call_args_list[1].kwargs["params"]
    assert second_params["offset"] == limit
    assert session.get.call_args_list[0].kwargs["timeout"] == 7.0


def test_fetch_records_handles_an_empty_response_without_paginating_further():
    session = MagicMock()
    session.get.return_value = _mock_response(200, {"total_count": 0, "results": []})

    client = OdreClient(_config(), session=session)
    records = list(
        client.fetch_records("eco2mix-national-tr", where="date = '2024-01-03'", fields=("date",))
    )

    assert records == []
    assert session.get.call_count == 1


def test_fetch_records_retries_on_429_then_succeeds():
    session = MagicMock()
    session.get.side_effect = [
        _mock_response(429),
        _mock_response(200, {"total_count": 1, "results": [{"date": "2024-01-01"}]}),
    ]

    client = OdreClient(_config(), session=session)
    records = list(
        client.fetch_records("eco2mix-national-tr", where="date = '2024-01-01'", fields=("date",))
    )

    assert records == [{"date": "2024-01-01"}]
    assert session.get.call_count == 2


def test_fetch_records_retries_on_500_and_raises_once_retries_are_exhausted():
    session = MagicMock()
    session.get.return_value = _mock_response(500)

    client = OdreClient(_config(max_retries=2), session=session)

    with pytest.raises(OdreApiError):
        list(
            client.fetch_records(
                "eco2mix-national-tr", where="date = '2024-01-01'", fields=("date",)
            )
        )

    assert session.get.call_count == 3  # initial attempt + 2 retries


def test_fetch_records_does_not_retry_on_a_client_error():
    session = MagicMock()
    session.get.return_value = _mock_response(404, {"error": "not found"})

    client = OdreClient(_config(max_retries=2), session=session)

    with pytest.raises(OdreApiError):
        list(
            client.fetch_records(
                "eco2mix-national-tr", where="date = '2024-01-01'", fields=("date",)
            )
        )

    assert session.get.call_count == 1


def test_fetch_records_retries_on_timeout_then_succeeds():
    import requests

    session = MagicMock()
    session.get.side_effect = [
        requests.exceptions.Timeout("boom"),
        _mock_response(200, {"total_count": 1, "results": [{"date": "2024-01-01"}]}),
    ]

    client = OdreClient(_config(), session=session)
    records = list(
        client.fetch_records("eco2mix-national-tr", where="date = '2024-01-01'", fields=("date",))
    )

    assert records == [{"date": "2024-01-01"}]
    assert session.get.call_count == 2
