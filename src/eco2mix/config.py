from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "https://opendata.reseaux-energies.fr/api/explore/v2.1"


@dataclass(frozen=True)
class Config:
    api_base_url: str
    request_timeout_seconds: float
    max_retries: int
    retry_backoff_base_seconds: float
    page_size: int
    raw_data_dir: Path
    duckdb_path: Path


def load_config(env_file: str | Path | None = ".env") -> Config:
    """Build the pipeline configuration from environment variables.

    Reads `env_file` first (via python-dotenv, without overriding variables
    already set in the environment) so a missing .env falls back cleanly to
    the defaults below — the ODRE API needs no key, so an empty environment
    is a valid configuration.
    """
    if env_file is not None:
        load_dotenv(env_file, override=False)

    return Config(
        api_base_url=os.environ.get("ECO2MIX_API_BASE_URL", DEFAULT_API_BASE_URL),
        request_timeout_seconds=float(os.environ.get("ECO2MIX_REQUEST_TIMEOUT_SECONDS", "30")),
        max_retries=int(os.environ.get("ECO2MIX_MAX_RETRIES", "5")),
        retry_backoff_base_seconds=float(os.environ.get("ECO2MIX_RETRY_BACKOFF_BASE_SECONDS", "1")),
        page_size=int(os.environ.get("ECO2MIX_PAGE_SIZE", "100")),
        raw_data_dir=Path(os.environ.get("ECO2MIX_RAW_DATA_DIR", "data/raw")),
        duckdb_path=Path(os.environ.get("ECO2MIX_DUCKDB_PATH", "warehouse.duckdb")),
    )
