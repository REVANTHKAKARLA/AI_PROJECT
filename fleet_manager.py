"""
fleet_manager.py

Defines the FleetManager class for managing a fleet of vehicles.
"""

from typing import List, Optional, Dict
import logging

from vehicle import Vehicle
from config import CRITICAL_OVERHEAT_TEMP, LOW_FUEL_THRESHOLD


class FleetManager:
    """
    Manages a fleet of Vehicle objects, computes statistics, and checks alerts.
    """

    def __init__(self, vehicles: Optional[List[Vehicle]] = None) -> None:
        """
        Initialize the FleetManager.

        Args:
            vehicles (Optional[List[Vehicle]]): List of Vehicle objects.
        """
        # Use an empty list if None is provided to avoid mutable default args
        self.vehicles: List[Vehicle] = vehicles if vehicles is not None else []

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a Vehicle to the fleet."""
        self.vehicles.append(vehicle)

    def average_speed(self) -> Optional[float]:
        """Compute average speed. Returns None if no vehicles."""
        if not self.vehicles:
            return None
        # Using generator expression for memory efficiency on large fleets
        return sum(v.speed for v in self.vehicles) / len(self.vehicles)

    def average_temperature(self) -> Optional[float]:
        """Compute average temperature. Returns None if no vehicles."""
        if not self.vehicles:
            return None
        return sum(v.temperature for v in self.vehicles) / len(self.vehicles)

    def average_fuel(self) -> Optional[float]:
        """Compute average fuel. Returns None if no vehicles."""
        if not self.vehicles:
            return None
        return sum(v.fuel for v in self.vehicles) / len(self.vehicles)

    def get_alerts(self) -> List[Dict[str, str]]:
        """
        Check all vehicles for alert conditions.

        Returns:
            List[Dict[str, str]]: List of alerts with vehicle id and message.
        """
        alerts: List[Dict[str, str]] = []
        for v in self.vehicles:
            if v.temperature > CRITICAL_OVERHEAT_TEMP:
                msg = "Critical Overheating"
                alerts.append({"id": v.id, "alert": msg})
                logging.warning(f"Vehicle {v.id}: {msg} (Temperature: {v.temperature}°C)")
            if v.fuel < LOW_FUEL_THRESHOLD:
                msg = "Low Fuel Warning"
                alerts.append({"id": v.id, "alert": msg})
                logging.warning(f"Vehicle {v.id}: {msg} (Fuel: {v.fuel}%)")
        return alerts

    def summary(self) -> str:
        """
        Returns a summary string of all vehicles.

        Returns:
            str: Summary of vehicles.
        """
        if not self.vehicles:
            return "No vehicles in the fleet."
        # Join string representations of vehicles line by line
        return "\n".join(str(v) for v in self.vehicles)


