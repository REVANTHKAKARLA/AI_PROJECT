"""
config.py

Centralized configuration and thresholds for the Fleet Management system.

Keeping constants in a single place improves maintainability and avoids
duplication across modules.
"""

# Validation bounds for Vehicle fields
MAX_SPEED = 300  # km/h
MIN_SPEED = 0
MAX_TEMPERATURE = 200  # Celsius
MIN_TEMPERATURE = -50
MAX_FUEL = 100  # percent
MIN_FUEL = 0

# Alert thresholds (tunable per deployment/environment)
CRITICAL_OVERHEAT_TEMP = 110  # Celsius (trigger when > threshold)
LOW_FUEL_THRESHOLD = 15       # Percent (trigger when < threshold)


