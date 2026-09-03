import datetime as dt

import duckdb
import pytest

from eco2mix.config import Config
from eco2mix.ingest.datasets import DATASETS
from eco2mix.ingest.runner import ingest_day
from eco2mix.load import TABLE_NAMES, connect, load_all, load_dataset


def _config(tmp_path) -> Config:
    return Config(
        api_base_url="unused",
        request_timeout_seconds=1.0,
        max_retries=0,
        retry_backoff_base_seconds=0.0,
        page_size=1000,
        raw_data_dir=tmp_path / "raw",
        duckdb_path=tmp_path / "warehouse.duckdb",
    )


class FakeClient:
    def __init__(self, records_by_day: dict[str, list[dict]]) -> None:
        self._records_by_day = records_by_day

    def fetch_records(self, dataset_id: str, *, where: str, fields):
        day = where.split("'")[1]
        for record in self._records_by_day.get(day, []):
            yield {field: record.get(field) for field in fields}


def _ingest_two_partitions(config: Config, dataset_id: str) -> None:
    spec = DATASETS[dataset_id]
    client = FakeClient(
        {
            "2024-01-01": [{field: field for field in spec.fields}],
            "2024-01-02": [{field: field for field in spec.fields}],
        }
    )
    ingest_day(client, config, spec, dt.date(2024, 1, 1))
    ingest_day(client, config, spec, dt.date(2024, 1, 2))


def test_load_dataset_reads_every_partition_ignoring_the_hive_path(tmp_path):
    config = _config(tmp_path)
    _ingest_two_partitions(config, "eco2mix-national-tr")

    con = connect(config)
    try:
        count = load_dataset(con, config, "eco2mix-national-tr")

        assert count == 2
        table_rows = con.execute(
            f"SELECT date FROM {TABLE_NAMES['eco2mix-national-tr']}"
        ).fetchall()
        # The physical "date" column survives untouched (not overridden by
        # the "date=..." partition folder name), proving hive_partitioning
        # was actually disabled rather than just not mattering here.
        assert sorted(r[0] for r in table_rows) == ["date", "date"]
    finally:
        con.close()


def test_load_dataset_rerun_replaces_rather_than_appends(tmp_path):
    config = _config(tmp_path)
    _ingest_two_partitions(config, "eco2mix-national-tr")

    con = connect(config)
    try:
        load_dataset(con, config, "eco2mix-national-tr")
        count = load_dataset(con, config, "eco2mix-national-tr")
        assert count == 2  # not 4: CREATE OR REPLACE, not an append
    finally:
        con.close()


def test_load_all_loads_the_three_datasets_into_their_own_tables(tmp_path):
    config = _config(tmp_path)
    for dataset_id in DATASETS:
        _ingest_two_partitions(config, dataset_id)

    con = connect(config)
    try:
        counts = load_all(con, config)

        assert counts == {dataset_id: 2 for dataset_id in DATASETS}
        existing_tables = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        assert set(TABLE_NAMES.values()) <= existing_tables
    finally:
        con.close()


def test_load_dataset_without_any_ingested_partition_raises(tmp_path):
    config = _config(tmp_path)
    con = connect(config)
    try:
        with pytest.raises(duckdb.IOException):
            load_dataset(con, config, "eco2mix-national-tr")
    finally:
        con.close()
