"""
io_utils.py

CSV I/O utilities for the Fleet Management system. Separated to keep `main.py`
focused on orchestration while making the loader importable for tests and tools.
"""

from __future__ import annotations

import csv
import logging
from typing import Iterable, Iterator, List, Optional

from vehicle import Vehicle


def iter_vehicles_from_csv(file_path: str, strict: bool = False) -> Iterator[Vehicle]:
    """
    Stream vehicles from a CSV file lazily.

    strict=False: skip malformed rows with logging.
    strict=True: raise ValueError on the first malformed row.
    """
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for idx, row in enumerate(reader, start=1):
                if not row or len(row) < 4:
                    msg = f"Row {idx}: Missing values. Skipping row: {row}"
                    if strict:
                        raise ValueError(msg)
                    logging.error(msg)
                    continue
                try:
                    yield Vehicle(*row[:4])  # ignore extra columns
                except ValueError as e:
                    msg = f"Row {idx}: {e}. Skipping row."
                    if strict:
                        raise ValueError(msg)
                    logging.error(msg)
    except FileNotFoundError:
        logging.critical(f"CSV file '{file_path}' not found.")
        raise


def load_vehicles_from_csv(file_path: str, strict: bool = False) -> List[Vehicle]:
    """
    Load vehicles from a CSV file with rows: id,speed,temperature,fuel.

    Robust to empty files, missing fields, and invalid types. Invalid rows are
    logged and skipped. Returns only valid vehicles.
    """
    return list(iter_vehicles_from_csv(file_path, strict=strict))


