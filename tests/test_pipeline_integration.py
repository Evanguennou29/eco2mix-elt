"""End-to-end pipeline test: frozen fixtures -> Parquet -> DuckDB raw tables.

No network call — the fixtures stand in for the ODRE API, exactly like the
FixtureClient in scripts/build_fixture_warehouse.py (which CI uses to run
`dbt build`). This test covers the Python side of that same path; the dbt
staging layer itself is exercised by `dbt build` in CI, not here, since
running dbt from pytest would duplicate that CI step for no extra
confidence.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from eco2mix.config import Config
from eco2mix.ingest.datasets import DATASETS
from eco2mix.ingest.runner import ingest_range
from eco2mix.load import TABLE_NAMES, connect, load_all

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class FixtureClient:
    def __init__(self, dataset_id: str) -> None:
        self._dataset_dir = FIXTURES_DIR / dataset_id

    def fetch_records(self, dataset_id: str, *, where: str, fields):
        day = where.split("'")[1]
        payload = json.loads((self._dataset_dir / f"{day}.json").read_text(encoding="utf-8"))
        for record in payload["results"]:
            yield {field: record.get(field) for field in fields}


def _fixture_days(dataset_id: str) -> list[dt.date]:
    return sorted(dt.date.fromisoformat(p.stem) for p in (FIXTURES_DIR / dataset_id).glob("*.json"))


@pytest.fixture
def warehouse(tmp_path):
    config = Config(
        api_base_url="unused",
        request_timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_base_seconds=0.0,
        page_size=1000,
        raw_data_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "warehouse.duckdb",
    )
    for dataset_id, spec in DATASETS.items():
        client = FixtureClient(dataset_id)
        for day in _fixture_days(dataset_id):
            ingest_range(client, config, spec, day, day)

    con = connect(config)
    try:
        yield con, config
    finally:
        con.close()


def test_every_fixture_dataset_has_at_least_two_days_of_data():
    for dataset_id in DATASETS:
        assert len(_fixture_days(dataset_id)) >= 2, dataset_id


def test_raw_tables_are_loaded_for_all_three_datasets(warehouse):
    con, config = warehouse
    counts = load_all(con, config)

    assert set(counts) == set(DATASETS)
    assert all(count > 0 for count in counts.values())
    for table_name in TABLE_NAMES.values():
        assert con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0] > 0


def test_raw_national_tr_carries_the_fields_the_staging_model_relies_on(warehouse):
    con, config = warehouse
    load_all(con, config, ["eco2mix-national-tr"])

    columns = {
        row[0] for row in con.execute(f"DESCRIBE {TABLE_NAMES['eco2mix-national-tr']}").fetchall()
    }
    assert {"date_heure", "perimetre", "nature", "consommation", "taux_co2"} <= columns
