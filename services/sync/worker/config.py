"""
Sync V1 Worker — configuration.

All settings are self-contained. No production config.py changes.
Defaults are safe for local development; override via environment variables.
"""

from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


class WorkerConfig:
    """Worker-specific configuration. Lives entirely in this module."""

    # --- Sync target ---
    SYNC_TARGET_URL: str = _env("SYNC_TARGET_URL", "http://82.115.8.100:8000")
    SYNC_API_KEY: str = _env("SYNC_API_KEY", "")

    # --- Chunking (reuse existing chunker defaults) ---
    SYNC_CHUNK_SIZE: int = _env_int("SYNC_CHUNK_SIZE", 5120)
    SYNC_BATCH_SIZE: int = _env_int("SYNC_BATCH_SIZE", 100)

    # --- Retry ---
    SYNC_RETRY_MAX: int = _env_int("SYNC_RETRY_MAX", 3)
    SYNC_RETRY_BASE_DELAY: float = float(_env("SYNC_RETRY_BASE_DELAY", "1"))
    SYNC_RETRY_MAX_DELAY: float = float(_env("SYNC_RETRY_MAX_DELAY", "60"))

    # --- State ---
    SYNC_STATE_DIR: str = _env("SYNC_STATE_DIR", "data/sync/worker")

    # --- Scheduling ---
    SYNC_SCHEDULE_SECONDS: int = _env_int("SYNC_SCHEDULE_SECONDS", 300)

    # --- Enable/disable ---
    SYNC_ENABLED: bool = _env_bool("SYNC_ENABLED", False)

    # --- Source ---
    SYNC_SOURCE: str = _env("SYNC_SOURCE", "iran-gateway")
    SYNC_TARGET: str = _env("SYNC_TARGET", "external-server")
