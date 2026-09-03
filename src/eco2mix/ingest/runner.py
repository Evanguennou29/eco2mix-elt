"""Extract a date range for one ODRE dataset to date-partitioned Parquet.

Each day is written atomically (write to a temp file, then rename into
place), so re-running the same date range overwrites each day's partition
cleanly instead of duplicating rows or leaving a half-written file behind.
This matters because ODRE reissues recent periods as "consolidated" then
"definitive" data — re-ingesting a date range is the normal way to pick up
those revisions, not an edge case.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from typing import TYPE_CHECKING, Protocol

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from pathlib import Path

    from eco2mix.config import Config
    from eco2mix.ingest.datasets import DatasetSpec


class RecordSource(Protocol):
    def fetch_records(self, dataset_id: str, *, where: str, fields) -> Iterator[dict]: ...


def date_range(start: dt.date, end: dt.date) -> Iterator[dt.date]:
    """Yield every date from `start` to `end`, inclusive of both bounds."""
    if end < start:
        raise ValueError(f"end date {end} is before start date {start}")
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


def partition_path(raw_dir: Path, dataset_id: str, day: dt.date) -> Path:
    return raw_dir / dataset_id / f"date={day.isoformat()}" / "data.parquet"


def ingest_day(client: RecordSource, config: Config, spec: DatasetSpec, day: dt.date) -> Path:
    """Fetch one day for `spec` and (re)write its Parquet partition."""
    where = f"{spec.date_field} = '{day.isoformat()}'"
    records = list(client.fetch_records(spec.dataset_id, where=where, fields=spec.fields))
    table = _records_to_table(records, spec.fields)

    path = partition_path(config.raw_data_dir, spec.dataset_id, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp_path)
    tmp_path.replace(path)
    return path


def ingest_range(
    client: RecordSource, config: Config, spec: DatasetSpec, start: dt.date, end: dt.date
) -> list[Path]:
    """Ingest every day in [start, end] for `spec`, one partition per day."""
    return [ingest_day(client, config, spec, day) for day in date_range(start, end)]


def _records_to_table(records: list[dict], fields: tuple[str, ...]) -> pa.Table:
    columns = {field: [record.get(field) for record in records] for field in fields}
    return pa.table(columns)
