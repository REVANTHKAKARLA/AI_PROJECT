"""
vehicle.py

Defines the Vehicle class for the Fleet Management System.
"""

from typing import Any
from config import (
    MAX_SPEED,
    MIN_SPEED,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    MAX_FUEL,
    MIN_FUEL,
)


class Vehicle:
    """
    Represents a vehicle with id, speed, temperature, and fuel level.

    Attributes:
        id (str): Unique identifier for the vehicle.
        speed (int): Current speed in km/h.
        temperature (int): Engine temperature in Celsius.
        fuel (int): Fuel level as a percentage (0-100).
    """

    def __init__(self, id: str, speed: Any, temperature: Any, fuel: Any) -> None:
        """
        Initialize a Vehicle object with input validation.

        Args:
            id (str): Vehicle identifier.
            speed (Any): Speed value, will be validated and cast to int.
            temperature (Any): Temperature value, validated and cast to int.
            fuel (Any): Fuel value, validated and cast to int.

        Raises:
            ValueError: If any input is invalid.
        """
        # Validate id
        if not isinstance(id, str) or not id.strip():
            raise ValueError("Vehicle id must be a non-empty string.")
        self.id = id.strip()

        # Validate and cast speed
        try:
            speed = int(speed)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid speed for vehicle {self.id}: {speed}")
        if not (MIN_SPEED <= speed <= MAX_SPEED):
            raise ValueError(f"Speed {speed} out of range for vehicle {self.id}.")
        self.speed = speed

        # Validate and cast temperature
        try:
            temperature = int(temperature)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid temperature for vehicle {self.id}: {temperature}")
        if not (MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE):
            raise ValueError(f"Temperature {temperature} out of range for vehicle {self.id}.")
        self.temperature = temperature

        # Validate and cast fuel
        try:
            fuel = int(fuel)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid fuel for vehicle {self.id}: {fuel}")
        if not (MIN_FUEL <= fuel <= MAX_FUEL):
            raise ValueError(f"Fuel {fuel} out of range for vehicle {self.id}.")
        self.fuel = fuel

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (f"Vehicle(id={self.id}, speed={self.speed} km/h, "
                f"temperature={self.temperature}°C, fuel={self.fuel}%)")

    def __repr__(self) -> str:
        """Unambiguous string representation."""
        return (f"Vehicle(id={repr(self.id)}, speed={self.speed}, "
                f"temperature={self.temperature}, fuel={self.fuel})")


