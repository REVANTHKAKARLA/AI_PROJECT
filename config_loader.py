"""
config_loader.py

Lightweight configuration overrides via environment variables or a JSON file.
Defaults remain in config.py; this module can modify them at runtime before
any Vehicles are constructed to keep behavior backward-compatible.

We intentionally avoid YAML to keep zero third-party dependencies.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import config as cfg


ENV_MAP = {
    "FM_CRITICAL_OVERHEAT_TEMP": "CRITICAL_OVERHEAT_TEMP",
    "FM_LOW_FUEL_THRESHOLD": "LOW_FUEL_THRESHOLD",
    "FM_MIN_SPEED": "MIN_SPEED",
    "FM_MAX_SPEED": "MAX_SPEED",
    "FM_MIN_TEMPERATURE": "MIN_TEMPERATURE",
    "FM_MAX_TEMPERATURE": "MAX_TEMPERATURE",
    "FM_MIN_FUEL": "MIN_FUEL",
    "FM_MAX_FUEL": "MAX_FUEL",
}


def _coerce_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def apply_env_overrides() -> None:
    """Apply environment variable overrides to config constants if present."""
    for env_key, cfg_attr in ENV_MAP.items():
        if env_key in os.environ:
            coerced = _coerce_int(os.environ[env_key])
            if coerced is not None:
                setattr(cfg, cfg_attr, coerced)


def apply_json_file_overrides(path: str) -> None:
    """Apply overrides from a JSON file; ignores unknown keys.

    Expected keys match names in config.py (e.g., CRITICAL_OVERHEAT_TEMP).
    """
    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    for key, value in data.items():
        if hasattr(cfg, key):
            coerced = _coerce_int(value)
            if coerced is not None:
                setattr(cfg, key, coerced)


def apply_overrides(config_json_path: Optional[str] = None) -> None:
    """Apply env and optional JSON config overrides in a safe order.

    Order: defaults (config.py) < JSON file < environment
    """
    if config_json_path:
        apply_json_file_overrides(config_json_path)
    apply_env_overrides()


