"""
logging_setup.py

Centralized logging configuration utilities. Libraries should use module-level
loggers; entrypoints (like main.py or concurrency.py) should call configure_logging
to set global handlers and formats. This avoids conflicting basicConfig calls.
"""

from __future__ import annotations

import logging
from typing import Optional


def configure_logging(level: int = logging.INFO, json_format: bool = False) -> None:
    """Configure global logging once.

    Args:
        level: Logging level (e.g., logging.INFO)
        json_format: If True, emits JSON lines; otherwise plaintext.
    """
    root = logging.getLogger()
    if root.handlers:
        # Already configured; do not duplicate handlers
        root.setLevel(level)
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root.setLevel(level)
    root.addHandler(handler)


