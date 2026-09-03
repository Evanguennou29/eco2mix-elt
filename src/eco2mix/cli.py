"""Entrypoint: `python -m eco2mix <command>`."""

from __future__ import annotations

import argparse
import datetime as dt

from eco2mix.config import load_config
from eco2mix.ingest.client import OdreClient
from eco2mix.ingest.datasets import DATASETS
from eco2mix.ingest.runner import ingest_range
from eco2mix.load import TABLE_NAMES, connect, load_all


def _parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eco2mix")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="Extract ODRE datasets to date-partitioned Parquet under data/raw/"
    )
    ingest_parser.add_argument("--start", type=_parse_date, required=True, help="YYYY-MM-DD")
    ingest_parser.add_argument("--end", type=_parse_date, required=True, help="YYYY-MM-DD")
    ingest_parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS),
        action="append",
        dest="datasets",
        help="Dataset to ingest; repeatable. Defaults to all three in scope.",
    )

    load_parser = subparsers.add_parser(
        "load", help="Load Parquet partitions from data/raw/ into DuckDB raw_* tables"
    )
    load_parser.add_argument(
        "--dataset",
        choices=sorted(DATASETS),
        action="append",
        dest="datasets",
        help="Dataset to load; repeatable. Defaults to all three in scope.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        config = load_config()
        client = OdreClient(config)
        dataset_ids = args.datasets or sorted(DATASETS)
        for dataset_id in dataset_ids:
            spec = DATASETS[dataset_id]
            paths = ingest_range(client, config, spec, args.start, args.end)
            print(f"{dataset_id}: wrote {len(paths)} partition(s) to {config.raw_data_dir}")

    elif args.command == "load":
        config = load_config()
        con = connect(config)
        try:
            counts = load_all(con, config, args.datasets)
        finally:
            con.close()
        for dataset_id, count in counts.items():
            print(f"{dataset_id}: loaded {count} row(s) into {TABLE_NAMES[dataset_id]}")

    return 0
