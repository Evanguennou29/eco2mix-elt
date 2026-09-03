import datetime as dt
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from eco2mix.config import Config
from eco2mix.ingest.datasets import DatasetSpec
from eco2mix.ingest.runner import date_range, ingest_day, ingest_range, partition_path

SPEC = DatasetSpec(
    dataset_id="eco2mix-national-tr",
    date_field="date",
    fields=("date", "heure", "consommation"),
)


class FakeClient:
    """Stands in for OdreClient: returns canned records per `where` clause,
    with no HTTP call involved."""

    def __init__(self, records_by_day: dict[str, list[dict]]) -> None:
        self._records_by_day = records_by_day
        self.calls: list[str] = []

    def fetch_records(self, dataset_id: str, *, where: str, fields):
        self.calls.append(where)
        day = where.split("'")[1]
        for record in self._records_by_day.get(day, []):
            yield {field: record.get(field) for field in fields}


def _read(path: Path):
    # A plain ParquetFile read, not pq.read_table: the partition path looks
    # like .../date=2024-01-01/data.parquet, and pq.read_table's dataset
    # discovery would treat "date=..." as a Hive partition column and
    # collide it with the "date" column already stored in the file.
    return pq.ParquetFile(str(path)).read()


def _config(tmp_path: Path) -> Config:
    return Config(
        api_base_url="https://example.test/api/explore/v2.1",
        request_timeout_seconds=5.0,
        max_retries=1,
        retry_backoff_base_seconds=0.0,
        page_size=100,
        raw_data_dir=tmp_path,
        duckdb_path=tmp_path / "warehouse.duckdb",
    )


def test_date_range_is_inclusive_of_both_bounds():
    days = list(date_range(dt.date(2024, 1, 1), dt.date(2024, 1, 3)))
    assert days == [dt.date(2024, 1, 1), dt.date(2024, 1, 2), dt.date(2024, 1, 3)]


def test_date_range_of_a_single_day():
    assert list(date_range(dt.date(2024, 1, 1), dt.date(2024, 1, 1))) == [dt.date(2024, 1, 1)]


def test_date_range_rejects_an_end_date_before_the_start_date():
    with pytest.raises(ValueError):
        list(date_range(dt.date(2024, 1, 3), dt.date(2024, 1, 1)))


def test_ingest_day_writes_a_parquet_partition_with_the_expected_columns(tmp_path):
    client = FakeClient(
        {"2024-01-01": [{"date": "2024-01-01", "heure": "00:00", "consommation": 45000}]}
    )
    config = _config(tmp_path)

    path = ingest_day(client, config, SPEC, dt.date(2024, 1, 1))

    assert path == partition_path(config.raw_data_dir, SPEC.dataset_id, dt.date(2024, 1, 1))
    assert client.calls == ["date = '2024-01-01'"]
    table = _read(path)
    assert table.column_names == list(SPEC.fields)
    assert table.num_rows == 1
    assert table.column("consommation").to_pylist() == [45000]


def test_ingest_day_handles_an_empty_day_without_error(tmp_path):
    client = FakeClient({})
    config = _config(tmp_path)

    path = ingest_day(client, config, SPEC, dt.date(2024, 1, 2))

    table = _read(path)
    assert table.num_rows == 0
    assert table.column_names == list(SPEC.fields)


def test_ingest_day_is_idempotent_on_rerun(tmp_path):
    client = FakeClient(
        {
            "2024-01-01": [
                {"date": "2024-01-01", "heure": "00:00", "consommation": 1},
                {"date": "2024-01-01", "heure": "00:15", "consommation": 2},
            ]
        }
    )
    config = _config(tmp_path)

    ingest_day(client, config, SPEC, dt.date(2024, 1, 1))
    path = ingest_day(client, config, SPEC, dt.date(2024, 1, 1))

    files = list(path.parent.glob("*"))
    assert files == [path]  # exactly one file: overwritten, not duplicated
    table = _read(path)
    assert table.num_rows == 2  # not doubled across the two runs


def test_ingest_day_rerun_reflects_revised_data(tmp_path):
    """Simulates ODRE reissuing a day as consolidated/definitive: rerunning
    the same day with different values must replace, not append."""
    client = FakeClient(
        {"2024-01-01": [{"date": "2024-01-01", "heure": "00:00", "consommation": 100}]}
    )
    config = _config(tmp_path)
    ingest_day(client, config, SPEC, dt.date(2024, 1, 1))

    revised_client = FakeClient(
        {"2024-01-01": [{"date": "2024-01-01", "heure": "00:00", "consommation": 999}]}
    )
    path = ingest_day(revised_client, config, SPEC, dt.date(2024, 1, 1))

    table = _read(path)
    assert table.num_rows == 1
    assert table.column("consommation").to_pylist() == [999]


def test_ingest_range_writes_one_partition_per_day(tmp_path):
    client = FakeClient(
        {
            "2024-01-01": [{"date": "2024-01-01", "heure": "00:00", "consommation": 1}],
            "2024-01-02": [{"date": "2024-01-02", "heure": "00:00", "consommation": 2}],
        }
    )
    config = _config(tmp_path)

    paths = ingest_range(client, config, SPEC, dt.date(2024, 1, 1), dt.date(2024, 1, 2))

    assert len(paths) == 2
    assert all(p.exists() for p in paths)
    assert client.calls == ["date = '2024-01-01'", "date = '2024-01-02'"]
