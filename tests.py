"""
tests.py

Comprehensive unit and integration tests for the Fleet Management project
(`vehicle.py`, `fleet_manager.py`, `main.py`) using unittest.

Coverage includes:
- Vehicle validation
- FleetManager averages and alerts
- Boundary conditions (exactly at thresholds)
- Edge cases (empty lists, malformed CSV, missing files)
- Integration: CSV loading and main entrypoint behavior

Run:
    python -m unittest -v
"""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import vehicle as vehicle_mod
import fleet_manager as fm_mod
import main as main_mod


class TestVehicleValidation(unittest.TestCase):
    """Unit tests validating `Vehicle` input constraints and string representations."""

    def test_valid_vehicle_creation(self):
        """Creates a valid Vehicle and checks attributes are set and sanitized."""
        v = vehicle_mod.Vehicle(" V1 ", 100, 90, 50)
        self.assertEqual(v.id, "V1")
        self.assertEqual(v.speed, 100)
        self.assertEqual(v.temperature, 90)
        self.assertEqual(v.fuel, 50)
        # __str__ should include all fields in human-friendly form
        s = str(v)
        self.assertIn("Vehicle(id=V1", s)

    def test_invalid_id_raises(self):
        """Empty id should raise ValueError."""
        with self.assertRaises(ValueError):
            vehicle_mod.Vehicle("", 100, 90, 50)

    def test_invalid_speed_type_raises(self):
        """Non-numeric speed should raise ValueError."""
        with self.assertRaises(ValueError):
            vehicle_mod.Vehicle("V1", "fast", 90, 50)

    def test_out_of_range_temperature_raises(self):
        """Temperature outside allowed range should raise ValueError."""
        with self.assertRaises(ValueError):
            vehicle_mod.Vehicle("V1", 100, vehicle_mod.MAX_TEMPERATURE + 1, 50)

    def test_out_of_range_fuel_raises(self):
        """Fuel outside 0..100 should raise ValueError."""
        with self.assertRaises(ValueError):
            vehicle_mod.Vehicle("V1", 100, 90, vehicle_mod.MAX_FUEL + 1)


class TestFleetManagerCalculations(unittest.TestCase):
    """Unit tests for average calculations over fleets of vehicles."""

    def setUp(self):
        # Sample data per requirements
        self.v1 = vehicle_mod.Vehicle("Vehicle1", 120, 120, 10)
        self.v2 = vehicle_mod.Vehicle("Vehicle2", 80, 90, 40)
        self.v3 = vehicle_mod.Vehicle("Vehicle3", 100, 110, 15)
        self.fleet = fm_mod.FleetManager([self.v1, self.v2, self.v3])

    def test_average_speed(self):
        """Average speed should be 100 for the sample dataset."""
        self.assertAlmostEqual(self.fleet.average_speed(), 100.0)

    def test_average_temperature(self):
        """Average temperature computed correctly."""
        expected = (120 + 90 + 110) / 3
        self.assertAlmostEqual(self.fleet.average_temperature(), expected)

    def test_average_fuel(self):
        """Average fuel computed correctly."""
        expected = (10 + 40 + 15) / 3
        self.assertAlmostEqual(self.fleet.average_fuel(), expected)

    def test_empty_fleet_returns_none_for_averages(self):
        """On empty fleets, averages return None (design choice in original code)."""
        empty = fm_mod.FleetManager([])
        self.assertIsNone(empty.average_speed())
        self.assertIsNone(empty.average_temperature())
        self.assertIsNone(empty.average_fuel())


class TestFleetManagerAlerts(unittest.TestCase):
    """Unit tests ensuring alert logic is correct, including thresholds and boundaries."""

    def test_alerts_triggered_correctly(self):
        """Vehicle1 should trigger both alerts; others should not for provided dataset."""
        v1 = vehicle_mod.Vehicle("Vehicle1", 120, 120, 10)
        v2 = vehicle_mod.Vehicle("Vehicle2", 80, 90, 40)
        v3 = vehicle_mod.Vehicle("Vehicle3", 100, 110, 15)
        fleet = fm_mod.FleetManager([v1, v2, v3])

        alerts = fleet.get_alerts()
        pairs = {(a["id"], a["alert"]) for a in alerts}

        self.assertIn(("Vehicle1", "Critical Overheating"), pairs)
        self.assertIn(("Vehicle1", "Low Fuel Warning"), pairs)
        # Boundary equals threshold should NOT trigger
        self.assertNotIn(("Vehicle3", "Critical Overheating"), pairs)
        self.assertNotIn(("Vehicle3", "Low Fuel Warning"), pairs)
        # Vehicle2 should have no alerts
        self.assertNotIn(("Vehicle2", "Critical Overheating"), pairs)
        self.assertNotIn(("Vehicle2", "Low Fuel Warning"), pairs)

    def test_boundary_exact_thresholds_do_not_alert(self):
        """Exactly at thresholds should not alert per '>' and '<' conditions."""
        at_temp = vehicle_mod.Vehicle("V_T", 50, fm_mod.CRITICAL_OVERHEAT_TEMP, 50)
        at_fuel = vehicle_mod.Vehicle("V_F", 50, 80, fm_mod.LOW_FUEL_THRESHOLD)
        fleet = fm_mod.FleetManager([at_temp, at_fuel])
        pairs = {(a["id"], a["alert"]) for a in fleet.get_alerts()}
        self.assertEqual(pairs, set())


class TestIntegrationCSV(unittest.TestCase):
    """Integration tests for CSV reading and interoperability between modules."""

    def setUp(self):
        # Temporary directory for test CSVs (Windows-safe)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _write_csv(self, name: str, lines: list[str]) -> str:
        path = os.path.join(self.tmp_dir.name, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_load_valid_csv(self):
        """Valid CSV should load 3 vehicles with correct fields."""
        csv_path = self._write_csv(
            "valid.csv",
            [
                "Vehicle1,120,120,10",
                "Vehicle2,80,90,40",
                "Vehicle3,100,110,15",
            ],
        )
        vehicles = main_mod.load_vehicles_from_csv(csv_path)
        self.assertEqual(len(vehicles), 3)
        self.assertEqual(vehicles[0].id, "Vehicle1")
        self.assertEqual(vehicles[2].temperature, 110)

    def test_load_csv_with_malformed_rows_skips_invalid(self):
        """Malformed lines (missing fields, non-numeric, out-of-range) are skipped."""
        csv_path = self._write_csv(
            "malformed.csv",
            [
                "V1,120,120,10",          # valid
                "V_BAD_ONLY_ID",           # missing fields
                "V2,fast,90,40",           # non-numeric speed
                f"V3,100,{vehicle_mod.MAX_TEMPERATURE + 5},50",  # temp out-of-range
                "V4,80,90,200",            # fuel out-of-range
                "V5,0,85,50",              # valid
            ],
        )
        vehicles = main_mod.load_vehicles_from_csv(csv_path)
        self.assertEqual(len(vehicles), 2)
        ids = {v.id for v in vehicles}
        self.assertEqual(ids, {"V1", "V5"})

    def test_load_missing_file_raises(self):
        """Non-existent CSV path should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            main_mod.load_vehicles_from_csv(os.path.join(self.tmp_dir.name, "nope.csv"))

    def test_load_empty_file_returns_empty_list(self):
        """Empty CSV should yield an empty list (graceful handling)."""
        csv_path = self._write_csv("empty.csv", [])
        vehicles = main_mod.load_vehicles_from_csv(csv_path)
        self.assertEqual(vehicles, [])


class TestMainIntegration(unittest.TestCase):
    """End-to-end tests for the `main` entrypoint using temporary CSV files and stdout capture."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)

    def _write_csv(self, name: str, lines: list[str]) -> str:
        path = os.path.join(self.tmp_dir.name, name)
        with open(path, "w", encoding="utf-8", newline="") as f:
            for line in lines:
                f.write(line + "\n")
        return path

    def test_main_with_valid_csv(self):
        """Main should return 0 and print summaries, averages, and expected alerts."""
        csv_path = self._write_csv(
            "valid.csv",
            [
                "Vehicle1,120,120,10",
                "Vehicle2,80,90,40",
                "Vehicle3,100,110,15",
            ],
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main_mod.main(["prog", csv_path])
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Fleet Summary:", output)
        self.assertIn("Vehicle(id=Vehicle1", output)
        self.assertIn("Averages:", output)
        self.assertIn("Alerts:", output)
        # Only Vehicle1 should have both alerts
        self.assertIn("Vehicle Vehicle1: Critical Overheating", output)
        self.assertIn("Vehicle Vehicle1: Low Fuel Warning", output)

    def test_main_with_missing_file(self):
        """Missing file should return exit code 1 and not crash."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main_mod.main(["prog", os.path.join(self.tmp_dir.name, "no.csv")])
        self.assertEqual(code, 1)

    def test_main_with_no_args(self):
        """No arguments should return usage (code 2)."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main_mod.main(["prog"])  # no CSV arg
        self.assertEqual(code, 2)

    def test_main_with_empty_csv(self):
        """Empty CSV should produce a summary indicating no vehicles and return 0."""
        csv_path = self._write_csv("empty.csv", [])
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main_mod.main(["prog", csv_path])
        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("No vehicles in the fleet.", output)


class TestEdgeCases(unittest.TestCase):
    """Additional edge-case tests: single vehicle and exact-threshold behavior."""

    def test_single_vehicle_averages_and_alerts(self):
        """Single vehicle should yield averages equal to its values and proper alerts behavior."""
        v = vehicle_mod.Vehicle("Solo", 50, fm_mod.CRITICAL_OVERHEAT_TEMP + 1, fm_mod.LOW_FUEL_THRESHOLD - 1)
        fleet = fm_mod.FleetManager([v])
        self.assertEqual(fleet.average_speed(), 50)
        self.assertEqual(fleet.average_temperature(), fm_mod.CRITICAL_OVERHEAT_TEMP + 1)
        self.assertEqual(fleet.average_fuel(), fm_mod.LOW_FUEL_THRESHOLD - 1)
        alerts = {(a["id"], a["alert"]) for a in fleet.get_alerts()}
        self.assertIn(("Solo", "Critical Overheating"), alerts)
        self.assertIn(("Solo", "Low Fuel Warning"), alerts)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
tests.py

Unit tests for vehicle.py and fleet_manager.py using unittest.
"""

import unittest
from vehicle import Vehicle
from fleet_manager import FleetManager


class TestVehicle(unittest.TestCase):
    def test_valid_vehicle(self):
        v = Vehicle("V1", 100, 90, 50)
        self.assertEqual(v.id, "V1")
        self.assertEqual(v.speed, 100)
        self.assertEqual(v.temperature, 90)
        self.assertEqual(v.fuel, 50)

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            Vehicle("", 100, 90, 50)

    def test_invalid_speed(self):
        with self.assertRaises(ValueError):
            Vehicle("V1", -10, 90, 50)
        with self.assertRaises(ValueError):
            Vehicle("V1", "fast", 90, 50)

    def test_invalid_temperature(self):
        with self.assertRaises(ValueError):
            Vehicle("V1", 100, 300, 50)
        with self.assertRaises(ValueError):
            Vehicle("V1", 100, "hot", 50)

    def test_invalid_fuel(self):
        with self.assertRaises(ValueError):
            Vehicle("V1", 100, 90, 200)
        with self.assertRaises(ValueError):
            Vehicle("V1", 100, 90, "full")


class TestFleetManager(unittest.TestCase):
    def setUp(self):
        self.v1 = Vehicle("V1", 120, 130, 10)
        self.v2 = Vehicle("V2", 80, 90, 40)
        self.v3 = Vehicle("V3", 0, 85, 50)
        self.fleet = FleetManager([self.v1, self.v2, self.v3])

    def test_average_speed(self):
        self.assertAlmostEqual(self.fleet.average_speed(), (120 + 80 + 0) / 3)

    def test_average_temperature(self):
        self.assertAlmostEqual(self.fleet.average_temperature(), (130 + 90 + 85) / 3)

    def test_average_fuel(self):
        self.assertAlmostEqual(self.fleet.average_fuel(), (10 + 40 + 50) / 3)

    def test_alerts(self):
        alerts = self.fleet.get_alerts()
        alert_types = {(a['id'], a['alert']) for a in alerts}
        self.assertIn(("V1", "Critical Overheating"), alert_types)
        self.assertIn(("V1", "Low Fuel Warning"), alert_types)
        self.assertNotIn(("V2", "Critical Overheating"), alert_types)
        self.assertNotIn(("V3", "Low Fuel Warning"), alert_types)

    def test_empty_fleet(self):
        empty_fleet = FleetManager([])
        self.assertIsNone(empty_fleet.average_speed())
        self.assertIsNone(empty_fleet.average_temperature())
        self.assertIsNone(empty_fleet.average_fuel())
        self.assertEqual(empty_fleet.get_alerts(), [])
        self.assertEqual(empty_fleet.summary(), "No vehicles in the fleet.")


if __name__ == "__main__":
    unittest.main()


