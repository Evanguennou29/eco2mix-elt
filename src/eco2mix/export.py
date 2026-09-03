"""Export dbt mart tables from DuckDB to versioned Parquet files.

This is the boundary the architecture diagram in SPEC.md calls out: the
dashboard never talks to DuckDB or the API, it only ever reads the frozen
Parquet files this module writes under data/marts/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from pathlib import Path

MART_TABLE_NAMES: tuple[str, ...] = (
    "mart_intensite_horaire",
    "mart_mix_regional",
    "mart_saisonnalite",
)


def export_mart(con: duckdb.DuckDBPyConnection, table_name: str, output_dir: Path) -> Path:
    """Write one mart table to <output_dir>/<table_name>.parquet.

    table_name is always one of our own fixed MART_TABLE_NAMES, never
    external input, so building the SQL by string formatting here does
    not open an injection surface.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{table_name}.parquet"
    escaped_path = str(path).replace("'", "''")
    con.execute(f"COPY {table_name} TO '{escaped_path}' (FORMAT PARQUET)")
    return path


def export_all(
    con: duckdb.DuckDBPyConnection, output_dir: Path, table_names: list[str] | None = None
) -> list[Path]:
    table_names = table_names or list(MART_TABLE_NAMES)
    return [export_mart(con, table_name, output_dir) for table_name in table_names]
