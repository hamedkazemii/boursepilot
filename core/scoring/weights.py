"""بارگذاری وزن‌ها و آستانه‌های امتیاز از YAML/config."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from config import settings

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "scoring.yaml"


def load_scoring_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path) if path else Path(getattr(settings, "SCORING_CONFIG_PATH", "") or _DEFAULT_PATH)
    if not cfg_path.exists():
        logger.warning("scoring config missing at %s — using built-in defaults", cfg_path)
        return _builtin_defaults()
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("scoring config must be a mapping")
    return data


def _builtin_defaults() -> dict[str, Any]:
    return {
        "weights": {
            "liquidity": 0.18,
            "orderbook_pressure": 0.20,
            "money_flow": 0.18,
            "momentum": 0.16,
            "volume_value": 0.14,
            "nav_premium": 0.14,
        },
        "redistribute_missing": True,
        "recommendation_thresholds": {
            "strong_buy": 80,
            "buy": 65,
            "neutral": 45,
            "weak": 30,
        },
        "labels": {
            "strong_buy": "خرید قوی",
            "buy": "خرید",
            "neutral": "خنثی",
            "weak": "ضعیف",
            "sell": "فروش",
        },
    }
