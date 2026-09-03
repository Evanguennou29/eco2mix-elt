"""Dagster assets for the eco2mix pipeline.

Lineage: three date-partitioned ingestion assets (one per ODRE dataset)
feed a single load asset that refreshes every DuckDB raw_* table, which
feeds the dbt staging/marts models (auto-loaded from the dbt project),
which feed the export step that writes the Parquet files the dashboard
reads. This mirrors the architecture diagram in SPEC.md, with Dagster in
the role it plays there: it triggers ingestion and the dbt build, nothing
downstream of that (the dashboard never talks to Dagster, the API, or
DuckDB — only to the frozen exported Parquet).
"""

import datetime as dt
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSpec,
    DailyPartitionsDefinition,
    Definitions,
    ScheduleDefinition,
    asset,
    build_schedule_from_partitioned_job,
    define_asset_job,
    multi_asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from eco2mix.config import load_config
from eco2mix.export import export_all
from eco2mix.ingest.client import OdreClient
from eco2mix.ingest.datasets import DATASETS
from eco2mix.ingest.runner import ingest_day
from eco2mix.load import connect, load_all

REPO_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = REPO_ROOT / "dbt"

# Matches SPEC.md's stated scope ("Historique consolidé de 2015 à
# aujourd'hui"). Only the partition *set* is defined by this start date —
# nothing runs until a schedule tick or a backfill asks for a partition.
daily_partitions = DailyPartitionsDefinition(start_date="2015-01-01")


def _ingest_partition(context: AssetExecutionContext, dataset_id: str) -> None:
    config = load_config()
    client = OdreClient(config)
    spec = DATASETS[dataset_id]
    day = dt.date.fromisoformat(context.partition_key)
    path = ingest_day(client, config, spec, day)
    context.log.info(f"{dataset_id}: wrote {path}")


@asset(partitions_def=daily_partitions, group_name="ingestion")
def raw_national_tr(context: AssetExecutionContext) -> None:
    """One day of eco2mix-national-tr, written to data/raw/ as Parquet.

    ingest_day overwrites its partition file atomically, so re-running a
    day (a backfill, or ODRE reissuing it as consolidated/definitive)
    replaces rather than duplicates.
    """
    _ingest_partition(context, "eco2mix-national-tr")


@asset(partitions_def=daily_partitions, group_name="ingestion")
def raw_national_cons_def(context: AssetExecutionContext) -> None:
    """One day of eco2mix-national-cons-def, written to data/raw/ as Parquet."""
    _ingest_partition(context, "eco2mix-national-cons-def")


@asset(partitions_def=daily_partitions, group_name="ingestion")
def raw_regional_tr(context: AssetExecutionContext) -> None:
    """One day of eco2mix-regional-tr, written to data/raw/ as Parquet."""
    _ingest_partition(context, "eco2mix-regional-tr")


# Asset keys must match what dagster-dbt derives from dbt/models/staging's
# `sources: raw` block (source name / table name), so the auto-generated
# dbt source assets resolve to these instead of spawning disconnected
# placeholder assets. One multi_asset, not three separate @asset
# functions: load_all() opens a single DuckDB connection and refreshes
# all three raw_* tables together in one call, which is the true unit of
# work — three ingestion assets feed it, but it is not separately
# re-runnable per table.
@multi_asset(
    specs=[
        AssetSpec(key=["raw", "national_tr"], deps=[raw_national_tr]),
        AssetSpec(key=["raw", "national_cons_def"], deps=[raw_national_cons_def]),
        AssetSpec(key=["raw", "regional_tr"], deps=[raw_regional_tr]),
    ],
    group_name="load",
)
def duckdb_raw_tables(context: AssetExecutionContext):
    """(Re)load every raw_* DuckDB table from whatever is under data/raw/.

    Not partitioned: load_dataset always rereads every Parquet partition
    for a dataset (CREATE OR REPLACE), so there is one current state per
    table, not one state per day.
    """
    config = load_config()
    con = connect(config)
    try:
        counts = load_all(con, config)
    finally:
        con.close()
    context.log.info(f"loaded row counts: {counts}")


dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path, project=dbt_project)
def eco2mix_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """stg_national, stg_regional, and the three marts — auto-loaded from
    dbt/models/. dagster-dbt derives each dbt source's asset key from its
    (source name, table name), which is why duckdb_raw_tables above uses
    the matching keys (["raw", "national_tr"], etc.) instead of its
    Python function name."""
    yield from dbt.cli(["build"], context=context).stream()


MART_ASSET_KEYS = [
    AssetKey("mart_intensite_horaire"),
    AssetKey("mart_mix_regional"),
    AssetKey("mart_saisonnalite"),
]


@asset(deps=MART_ASSET_KEYS, group_name="export")
def exported_marts(context: AssetExecutionContext) -> None:
    """Export the three dbt marts to data/marts/*.parquet — the only
    thing the dashboard (app/main.py) ever reads."""
    config = load_config()
    con = connect(config)
    try:
        paths = export_all(con, config.marts_dir)
    finally:
        con.close()
    for path in paths:
        context.log.info(f"wrote {path}")


ingest_job = define_asset_job(
    "ingest_job",
    selection=[raw_national_tr, raw_national_cons_def, raw_regional_tr],
    partitions_def=daily_partitions,
)

# Runs yesterday's partition every morning — the normal "day rolled over,
# ODRE has a new day of real-time data" trigger.
daily_ingest_schedule = build_schedule_from_partitioned_job(ingest_job, hour_of_day=6)

downstream_job = define_asset_job(
    "downstream_job",
    selection=[duckdb_raw_tables, eco2mix_dbt_assets, exported_marts],
)

# 30 minutes after ingestion, so the day's newly-ingested partitions are
# already on disk before the reload + dbt build + export runs.
daily_downstream_schedule = ScheduleDefinition(job=downstream_job, cron_schedule="30 6 * * *")

defs = Definitions(
    assets=[
        raw_national_tr,
        raw_national_cons_def,
        raw_regional_tr,
        duckdb_raw_tables,
        eco2mix_dbt_assets,
        exported_marts,
    ],
    jobs=[ingest_job, downstream_job],
    schedules=[daily_ingest_schedule, daily_downstream_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
