import datetime as dt

from eco2mix import cli
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
