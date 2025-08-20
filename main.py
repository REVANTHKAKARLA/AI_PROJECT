"""
main.py

Entry point for the Fleet Management System.
Loads vehicle data from a CSV file, manages the fleet, and prints reports.
"""

import sys
import logging
from typing import List, Optional

from fleet_manager import FleetManager
from io_utils import load_vehicles_from_csv
from config_loader import apply_overrides
from logging_setup import configure_logging

# CSV file path (can be parameterized via CLI args)
CSV_FILE = "vehicles.csv"


# Backwards-compat shim: keep same function available from main for existing imports/tests
from io_utils import load_vehicles_from_csv as _load_vehicles_from_csv
def load_vehicles_from_csv(file_path: str):
    return _load_vehicles_from_csv(file_path)


def main(argv: Optional[list[str]] = None) -> None:
    """
    Main function to run the Fleet Management System.
    """
    # Apply config overrides (JSON/env) before any objects are constructed
    # Keep defaults if no overrides provided
    configure_logging(level=logging.INFO)
    config_json = None
    # Simple argv parse without changing default behavior
    if argv is None:
        argv = sys.argv
    # Accept optional: program [csv_path] [config_json]
    file_path = argv[1] if len(argv) > 1 else CSV_FILE
    if len(argv) > 2:
        config_json = argv[2]
    if config_json:
        try:
            apply_overrides(config_json)
        except FileNotFoundError:
            logging.error("Config JSON not found: %s (continuing with defaults)", config_json)

    print("Fleet Management System\n" + "=" * 25)

    try:
        vehicles = load_vehicles_from_csv(file_path)
    except FileNotFoundError:
        print("Error: CSV file not found. Exiting.")
        sys.exit(1)

    fleet = FleetManager(vehicles)

    # Print summary
    print("\nFleet Summary:")
    print(fleet.summary())

    # Print averages
    avg_speed = fleet.average_speed()
    avg_temp = fleet.average_temperature()
    avg_fuel = fleet.average_fuel()
    print("\nAverages:")
    print(f"  Speed: {avg_speed:.2f} km/h" if avg_speed is not None else "  Speed: N/A")
    print(f"  Temperature: {avg_temp:.2f}°C" if avg_temp is not None else "  Temperature: N/A")
    print(f"  Fuel: {avg_fuel:.2f}%" if avg_fuel is not None else "  Fuel: N/A")

    # Print alerts
    alerts = fleet.get_alerts()
    print("\nAlerts:")
    if alerts:
        for alert in alerts:
            print(f"  Vehicle {alert['id']}: {alert['alert']}")
    else:
        print("  No alerts.")


if __name__ == "__main__":
    main()


