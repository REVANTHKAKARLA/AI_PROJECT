"""
refactored_fleet.py

A production-ready, OOP-based refactoring of the original list-based code for
managing vehicle data and alerts. This module is self-contained, includes
configurable thresholds, robust CSV loading with validation, and efficient
aggregations suitable for large datasets.

Run:
    python refactored_fleet.py vehicles.csv

Sample CSV (id,speed,temperature,fuel):
    V1,120,130,10
    V2,80,90,40
    V3,0,85,50

Notes:
- Thresholds and validation ranges are configurable via module-level constants.
- Uses type hints, docstrings, and logging for clarity and maintainability.
- For extremely large datasets, consider streaming processing or pandas.
"""

from __future__ import annotations

import csv
import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


# ---------------------------
# Configurable constants
# ---------------------------
# Validation ranges
MAX_SPEED = 300  # km/h
MIN_SPEED = 0
MAX_TEMPERATURE = 200  # Celsius
MIN_TEMPERATURE = -50
MAX_FUEL = 100  # percent
MIN_FUEL = 0

# Alert thresholds (magic numbers removed)
CRITICAL_OVERHEAT_TEMP = 110  # Celsius
LOW_FUEL_THRESHOLD = 15       # Percent


# ---------------------------
# Logging configuration
# ---------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------
# Domain model
# ---------------------------
@dataclass
class Vehicle:
    """
    Represents a vehicle with validated attributes.

    Attributes:
        id: Unique identifier for the vehicle.
        speed: Current speed in km/h.
        temperature: Engine temperature in Celsius.
        fuel: Fuel level as a percentage (0-100).

    Design notes:
    - Validation performed in __post_init__ to keep dataclass benefits while
      enforcing correctness.
    - Explicit ranges guard against outliers and corrupt data.
    """

    id: str
    speed: int
    temperature: int
    fuel: int

    def __post_init__(self) -> None:
        # Validate id
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Vehicle id must be a non-empty string.")
        self.id = self.id.strip()

        # Validate speed
        self.speed = Vehicle._coerce_int("speed", self.id, self.speed)
        if not (MIN_SPEED <= self.speed <= MAX_SPEED):
            raise ValueError(
                f"Speed {self.speed} out of range for vehicle {self.id}."
            )

        # Validate temperature
        self.temperature = Vehicle._coerce_int(
            "temperature", self.id, self.temperature
        )
        if not (MIN_TEMPERATURE <= self.temperature <= MAX_TEMPERATURE):
            raise ValueError(
                f"Temperature {self.temperature} out of range for vehicle {self.id}."
            )

        # Validate fuel
        self.fuel = Vehicle._coerce_int("fuel", self.id, self.fuel)
        if not (MIN_FUEL <= self.fuel <= MAX_FUEL):
            raise ValueError(
                f"Fuel {self.fuel} out of range for vehicle {self.id}."
            )

    @staticmethod
    def _coerce_int(field: str, vehicle_id: str, value: Any) -> int:
        """Convert value to int with a helpful error message on failure."""
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid {field} for vehicle {vehicle_id}: {value}"
            ) from exc

    def __str__(self) -> str:  # Human-readable
        return (
            f"Vehicle(id={self.id}, speed={self.speed} km/h, "
            f"temperature={self.temperature}°C, fuel={self.fuel}%)"
        )

    def __repr__(self) -> str:  # Debug-friendly
        return (
            f"Vehicle(id={self.id!r}, speed={self.speed}, "
            f"temperature={self.temperature}, fuel={self.fuel})"
        )


class FleetManager:
    """
    Manages a collection of vehicles; computes statistics and detects alerts.

    Methods return Optional[float] for averages on empty fleets to avoid
    division-by-zero and keep call sites explicit.
    """

    def __init__(self, vehicles: Optional[List[Vehicle]] = None) -> None:
        self.vehicles: List[Vehicle] = vehicles if vehicles is not None else []

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a Vehicle to the fleet."""
        self.vehicles.append(vehicle)

    # ---------- Aggregations ----------
    def average_speed(self) -> Optional[float]:
        if not self.vehicles:
            return None
        return sum(v.speed for v in self.vehicles) / len(self.vehicles)

    def average_temperature(self) -> Optional[float]:
        if not self.vehicles:
            return None
        return sum(v.temperature for v in self.vehicles) / len(self.vehicles)

    def average_fuel(self) -> Optional[float]:
        if not self.vehicles:
            return None
        return sum(v.fuel for v in self.vehicles) / len(self.vehicles)

    # ---------- Alerts ----------
    def get_alerts(self) -> List[Dict[str, str]]:
        """
        Check all vehicles for alert conditions.

        Returns:
            A list of {"id": <vehicle_id>, "alert": <message>}.
        """
        alerts: List[Dict[str, str]] = []
        for v in self.vehicles:
            if v.temperature > CRITICAL_OVERHEAT_TEMP:
                msg = "Critical Overheating"
                alerts.append({"id": v.id, "alert": msg})
                logger.warning(
                    "Vehicle %s: %s (Temperature: %s°C)", v.id, msg, v.temperature
                )
            if v.fuel < LOW_FUEL_THRESHOLD:
                msg = "Low Fuel Warning"
                alerts.append({"id": v.id, "alert": msg})
                logger.warning("Vehicle %s: %s (Fuel: %s%%)", v.id, msg, v.fuel)
        return alerts

    # ---------- Presentation ----------
    def summary(self) -> str:
        if not self.vehicles:
            return "No vehicles in the fleet."
        return "\n".join(str(v) for v in self.vehicles)


# ---------------------------
# CSV loading utilities
# ---------------------------
def load_vehicles_from_csv(file_path: str) -> List[Vehicle]:
    """
    Load vehicles from a CSV file with rows: id,speed,temperature,fuel.

    Robust to empty files, missing fields, and invalid types. Invalid rows are
    logged and skipped. Returns only valid vehicles.
    """
    vehicles: List[Vehicle] = []
    try:
        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for idx, row in enumerate(reader, start=1):
                if not row or len(row) < 4:
                    logger.error("Row %s: Missing values. Skipping: %s", idx, row)
                    continue
                try:
                    vehicle = Vehicle(*row[:4])  # Ignore extra columns
                    vehicles.append(vehicle)
                except ValueError as err:
                    logger.error("Row %s: %s. Skipping row.", idx, err)
    except FileNotFoundError as err:
        logger.critical("CSV file '%s' not found.", file_path)
        raise
    return vehicles


# ---------------------------
# CLI entry point
# ---------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """
    Application entry point.

    Args:
        argv: Optional list of arguments (for testing). If None, uses sys.argv.

    Returns:
        Exit status code (0 for success, non-zero for failure).
    """
    if argv is None:
        argv = sys.argv

    if len(argv) < 2:
        print("Usage: python refactored_fleet.py <vehicles.csv>")
        return 2

    csv_path = argv[1]

    print("Fleet Management System\n" + "=" * 25)

    try:
        vehicles = load_vehicles_from_csv(csv_path)
    except FileNotFoundError:
        print("Error: CSV file not found. Exiting.")
        return 1

    fleet = FleetManager(vehicles)

    # Summary
    print("\nFleet Summary:")
    print(fleet.summary())

    # Averages
    avg_speed = fleet.average_speed()
    avg_temp = fleet.average_temperature()
    avg_fuel = fleet.average_fuel()
    print("\nAverages:")
    print(f"  Speed: {avg_speed:.2f} km/h" if avg_speed is not None else "  Speed: N/A")
    print(
        f"  Temperature: {avg_temp:.2f}°C" if avg_temp is not None else "  Temperature: N/A"
    )
    print(f"  Fuel: {avg_fuel:.2f}%" if avg_fuel is not None else "  Fuel: N/A")

    # Alerts
    alerts = fleet.get_alerts()
    print("\nAlerts:")
    if alerts:
        for alert in alerts:
            print(f"  Vehicle {alert['id']}: {alert['alert']}")
    else:
        print("  No alerts.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


