"""Build warehouse.duckdb from the frozen test fixtures, with no network call.

Used by CI (see .github/workflows/ci.yml) and locally to run `dbt build`
against real fixture-shaped data instead of the live ODRE API: replays
tests/fixtures/<dataset>/<day>.json as if it were the API response for that
day, through the same ingest -> load code paths the CLI uses, then writes
data/raw/ and warehouse.duckdb at the repo root (both gitignored).
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator
from pathlib import Path

from eco2mix.config import Config
from eco2mix.ingest.datasets import DATASETS
from eco2mix.ingest.runner import ingest_range
from eco2mix.load import connect, load_all

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


class FixtureClient:
    """Replays one dataset's frozen JSON fixtures as ODRE API responses."""

    def __init__(self, dataset_id: str) -> None:
        self._dataset_dir = FIXTURES_DIR / dataset_id

    def fetch_records(self, dataset_id: str, *, where: str, fields) -> Iterator[dict]:
        day = where.split("'")[1]
        path = self._dataset_dir / f"{day}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload["results"]:
            yield {field: record.get(field) for field in fields}


def fixture_days(dataset_id: str) -> list[dt.date]:
    return sorted(dt.date.fromisoformat(p.stem) for p in (FIXTURES_DIR / dataset_id).glob("*.json"))


def build(config: Config) -> dict[str, int]:
    for dataset_id, spec in DATASETS.items():
        client = FixtureClient(dataset_id)
        for day in fixture_days(dataset_id):
            ingest_range(client, config, spec, day, day)

    con = connect(config)
    try:
        return load_all(con, config)
    finally:
        con.close()


def main() -> None:
    config = Config(
        api_base_url="unused",
        request_timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_base_seconds=0.0,
        page_size=1000,
        raw_data_dir=REPO_ROOT / "data" / "raw",
        duckdb_path=REPO_ROOT / "warehouse.duckdb",
        marts_dir=REPO_ROOT / "data" / "marts",
    )
    counts = build(config)
    for dataset_id, count in counts.items():
        print(f"{dataset_id}: loaded {count} row(s) from fixtures")


if __name__ == "__main__":
    main()
