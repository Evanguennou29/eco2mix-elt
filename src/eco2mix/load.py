"""Load partitioned Parquet from data/raw/ into DuckDB `raw_*` tables.

Each partition directory is named `date=YYYY-MM-DD` (see
`eco2mix.ingest.runner.partition_path`), but every Parquet file already
stores its own `date` column too. DuckDB's `read_parquet` auto-detects
Hive-style partitioning from that directory name by default and would
derive a second `date` column from the path — redundant with the column
already inside the file, and the reason pyarrow's own dataset reader
raised `ArrowTypeError: Unable to merge: Field date has incompatible
types` when a single partition file was read through its Hive-aware
dataset API during lot 1. We pass `hive_partitioning=false` explicitly
so DuckDB only ever reads what is physically stored in the files and
never infers anything from the directory structure — a glob still finds
every partition file, but reading is not coupled to how the auto-detect
heuristic decides to interpret the path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

from eco2mix.ingest.datasets import DATASETS

if TYPE_CHECKING:
    from eco2mix.config import Config

TABLE_NAMES: dict[str, str] = {
    "eco2mix-national-tr": "raw_national_tr",
    "eco2mix-national-cons-def": "raw_national_cons_def",
    "eco2mix-regional-tr": "raw_regional_tr",
}


def connect(config: Config) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(config.duckdb_path))


def load_dataset(con: duckdb.DuckDBPyConnection, config: Config, dataset_id: str) -> int:
    """(Re)create the raw table for one dataset from its Parquet partitions.

    Returns the row count loaded. Table names and dataset ids are both
    drawn from our own fixed internal maps, never from external input, so
    building the SQL by string formatting here does not open an injection
    surface.
    """
    table_name = TABLE_NAMES[dataset_id]
    pattern = (config.raw_data_dir / dataset_id / "*" / "*.parquet").as_posix()
    escaped_pattern = pattern.replace("'", "''")

    con.execute(
        f"CREATE OR REPLACE TABLE {table_name} AS "
        f"SELECT * FROM read_parquet('{escaped_pattern}', hive_partitioning=false)"
    )
    return con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]


def load_all(
    con: duckdb.DuckDBPyConnection, config: Config, dataset_ids: list[str] | None = None
) -> dict[str, int]:
    dataset_ids = dataset_ids or sorted(DATASETS)
    return {dataset_id: load_dataset(con, config, dataset_id) for dataset_id in dataset_ids}
