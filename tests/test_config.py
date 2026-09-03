from pathlib import Path

from eco2mix.config import DEFAULT_API_BASE_URL, load_config


def test_load_config_falls_back_to_defaults_without_env_file(monkeypatch, tmp_path):
    for key in (
        "ECO2MIX_API_BASE_URL",
        "ECO2MIX_REQUEST_TIMEOUT_SECONDS",
        "ECO2MIX_MAX_RETRIES",
        "ECO2MIX_RETRY_BACKOFF_BASE_SECONDS",
        "ECO2MIX_PAGE_SIZE",
        "ECO2MIX_RAW_DATA_DIR",
        "ECO2MIX_DUCKDB_PATH",
        "ECO2MIX_MARTS_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    config = load_config(env_file=tmp_path / "does-not-exist.env")

    assert config.api_base_url == DEFAULT_API_BASE_URL
    assert config.request_timeout_seconds == 30.0
    assert config.max_retries == 5
    assert config.retry_backoff_base_seconds == 1.0
    assert config.page_size == 100
    assert config.raw_data_dir == Path("data/raw")
    assert config.duckdb_path == Path("warehouse.duckdb")
    assert config.marts_dir == Path("data/marts")


def test_load_config_reads_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("ECO2MIX_API_BASE_URL", "https://example.test/api")
    monkeypatch.setenv("ECO2MIX_REQUEST_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("ECO2MIX_MAX_RETRIES", "1")
    monkeypatch.setenv("ECO2MIX_RETRY_BACKOFF_BASE_SECONDS", "0.5")
    monkeypatch.setenv("ECO2MIX_PAGE_SIZE", "50")
    monkeypatch.setenv("ECO2MIX_RAW_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ECO2MIX_DUCKDB_PATH", str(tmp_path / "test.duckdb"))
    monkeypatch.setenv("ECO2MIX_MARTS_DIR", str(tmp_path / "marts"))

    config = load_config(env_file=tmp_path / "does-not-exist.env")

    assert config.api_base_url == "https://example.test/api"
    assert config.request_timeout_seconds == 5.0
    assert config.max_retries == 1
    assert config.retry_backoff_base_seconds == 0.5
    assert config.page_size == 50
    assert config.raw_data_dir == tmp_path
    assert config.duckdb_path == tmp_path / "test.duckdb"
    assert config.marts_dir == tmp_path / "marts"
