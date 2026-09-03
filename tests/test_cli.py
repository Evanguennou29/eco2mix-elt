import datetime as dt
from pathlib import Path

from eco2mix import cli
from eco2mix.export import MART_TABLE_NAMES
from eco2mix.ingest.datasets import DATASETS


def test_ingest_command_ingests_all_datasets_by_default(monkeypatch):
    calls = []

    def fake_ingest_range(client, config, spec, start, end):
        calls.append((spec.dataset_id, start, end))
        return []

    monkeypatch.setattr(cli, "ingest_range", fake_ingest_range)

    exit_code = cli.main(["ingest", "--start", "2024-01-01", "--end", "2024-01-07"])

    assert exit_code == 0
    assert {dataset_id for dataset_id, _, _ in calls} == set(DATASETS)
    assert all(
        start == dt.date(2024, 1, 1) and end == dt.date(2024, 1, 7) for _, start, end in calls
    )


def test_ingest_command_can_target_a_single_dataset(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cli,
        "ingest_range",
        lambda client, config, spec, start, end: calls.append(spec.dataset_id) or [],
    )

    cli.main(
        [
            "ingest",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-01",
            "--dataset",
            "eco2mix-regional-tr",
        ]
    )

    assert calls == ["eco2mix-regional-tr"]


def test_ingest_command_rejects_a_malformed_date():
    parser = cli.build_parser()
    try:
        parser.parse_args(["ingest", "--start", "not-a-date", "--end", "2024-01-01"])
        raised = False
    except SystemExit:
        raised = True
    assert raised


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_load_command_loads_all_datasets_by_default(monkeypatch):
    fake_con = FakeConnection()
    monkeypatch.setattr(cli, "connect", lambda config: fake_con)

    calls = []

    def fake_load_all(con, config, dataset_ids):
        calls.append((con, dataset_ids))
        return dict.fromkeys(DATASETS, 0)

    monkeypatch.setattr(cli, "load_all", fake_load_all)

    exit_code = cli.main(["load"])

    assert exit_code == 0
    assert calls == [(fake_con, None)]
    assert fake_con.closed  # the connection is always closed, even on success


def test_load_command_can_target_a_single_dataset(monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda config: FakeConnection())
    calls = []
    monkeypatch.setattr(
        cli,
        "load_all",
        lambda con, config, dataset_ids: calls.append(dataset_ids) or {},
    )

    cli.main(["load", "--dataset", "eco2mix-regional-tr"])

    assert calls == [["eco2mix-regional-tr"]]


def test_load_command_closes_the_connection_even_if_loading_fails(monkeypatch):
    fake_con = FakeConnection()
    monkeypatch.setattr(cli, "connect", lambda config: fake_con)

    def failing_load_all(con, config, dataset_ids):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "load_all", failing_load_all)

    try:
        cli.main(["load"])
    except RuntimeError:
        pass

    assert fake_con.closed


def test_export_command_exports_all_marts_by_default(monkeypatch):
    fake_con = FakeConnection()
    monkeypatch.setattr(cli, "connect", lambda config: fake_con)

    calls = []

    def fake_export_all(con, output_dir, marts):
        calls.append((con, output_dir, marts))
        return [Path("data/marts") / f"{name}.parquet" for name in MART_TABLE_NAMES]

    monkeypatch.setattr(cli, "export_all", fake_export_all)

    exit_code = cli.main(["export"])

    assert exit_code == 0
    assert calls == [(fake_con, Path("data/marts"), None)]
    assert fake_con.closed


def test_export_command_can_target_a_single_mart(monkeypatch):
    monkeypatch.setattr(cli, "connect", lambda config: FakeConnection())
    calls = []
    monkeypatch.setattr(
        cli,
        "export_all",
        lambda con, output_dir, marts: calls.append(marts) or [],
    )

    cli.main(["export", "--mart", "mart_saisonnalite"])

    assert calls == [["mart_saisonnalite"]]


def test_export_command_closes_the_connection_even_if_exporting_fails(monkeypatch):
    fake_con = FakeConnection()
    monkeypatch.setattr(cli, "connect", lambda config: fake_con)

    def failing_export_all(con, output_dir, marts):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "export_all", failing_export_all)

    try:
        cli.main(["export"])
    except RuntimeError:
        pass

    assert fake_con.closed
