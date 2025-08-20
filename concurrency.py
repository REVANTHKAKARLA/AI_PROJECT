"""
concurrency.py

Threaded simulation and benchmarking for the Fleet Management project.

This module adds concurrency (via Python's threading module) to simulate
real-time updates of vehicle telemetry and compares single-threaded vs
multi-threaded performance while preserving correctness and thread-safety.

It DOES NOT modify existing project modules. It composes with:
  - vehicle.py (Vehicle + validation constants)
  - fleet_manager.py (FleetManager + thresholds)
  - main.py (CSV loader reused for data input)

Run examples:
    python concurrency.py vehicles.csv --iterations 5 --interval 1.0

Notes:
  - Per-vehicle Locks protect writers (update threads).
  - Aggregations acquire all vehicle locks in a stable order to prevent races.
  - This design avoids deadlocks by (a) writers acquiring a single lock and
    (b) readers acquiring all locks in a consistent global order.
"""

from __future__ import annotations

import argparse
import logging
import random
import threading
import time
from typing import Dict, Iterable, List, Tuple

from vehicle import (
    Vehicle,
    MIN_SPEED,
    MAX_SPEED,
    MIN_TEMPERATURE,
    MAX_TEMPERATURE,
    MIN_FUEL,
    MAX_FUEL,
)
from fleet_manager import FleetManager
import main as main_module


# ----------------------------------------------------------------------------
# Logging configuration (inherits root config if already set elsewhere)
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def clamp(value: int, low: int, high: int) -> int:
    """Return value constrained to [low, high]."""
    return high if value > high else low if value < low else value


def create_per_vehicle_locks(vehicles: Iterable[Vehicle]) -> Dict[str, threading.Lock]:
    """Create a Lock per vehicle id.

    Using vehicle id ensures stable ordering across runs and avoids identity-
    based surprises if Vehicle instances are cloned.
    """
    return {v.id: threading.Lock() for v in vehicles}


def acquire_all_vehicle_locks(vehicles: List[Vehicle], locks: Dict[str, threading.Lock]) -> None:
    """Acquire all vehicle locks in a stable, deterministic order to avoid deadlocks."""
    for vehicle_id in sorted((v.id for v in vehicles)):
        locks[vehicle_id].acquire()


def release_all_vehicle_locks(vehicles: List[Vehicle], locks: Dict[str, threading.Lock]) -> None:
    """Release all vehicle locks in reverse order for symmetry (order not critical)."""
    for vehicle_id in sorted((v.id for v in vehicles), reverse=True):
        locks[vehicle_id].release()


# ----------------------------------------------------------------------------
# Update logic (thread-safe writers)
# ----------------------------------------------------------------------------
def update_vehicle_once(vehicle: Vehicle, lock: threading.Lock) -> None:
    """Apply one simulated telemetry update to a vehicle under lock.

    - Speed changes by a small random delta in [-5, +5]
    - Temperature changes by a small random delta in [-2, +2]
    - Fuel decreases by a small random delta in [-1, 0]
    """
    with lock:
        new_speed = clamp(vehicle.speed + random.randint(-5, 5), MIN_SPEED, MAX_SPEED)
        new_temperature = clamp(
            vehicle.temperature + random.randint(-2, 2), MIN_TEMPERATURE, MAX_TEMPERATURE
        )
        new_fuel = clamp(vehicle.fuel + random.randint(-1, 0), MIN_FUEL, MAX_FUEL)

        vehicle.speed = new_speed
        vehicle.temperature = new_temperature
        vehicle.fuel = new_fuel


def vehicle_update_worker(vehicle: Vehicle, lock: threading.Lock, stop_event: threading.Event, interval_sec: float) -> None:
    """Thread target: periodically update a single vehicle until stop_event is set."""
    while not stop_event.is_set():
        update_vehicle_once(vehicle, lock)
        # Logging at DEBUG to avoid noisy output by default
        logger.debug("Updated %s -> speed=%s, temp=%s, fuel=%s", vehicle.id, vehicle.speed, vehicle.temperature, vehicle.fuel)
        # Sleep after update to simulate real telemetry tick
        stop_event.wait(interval_sec)


def start_vehicle_update_threads(
    vehicles: List[Vehicle],
    locks: Dict[str, threading.Lock],
    interval_sec: float,
) -> Tuple[List[threading.Thread], threading.Event]:
    """Start one thread per vehicle that updates its telemetry periodically.

    Returns the list of threads and a stop_event to signal termination.
    """
    stop_event = threading.Event()
    threads: List[threading.Thread] = []
    for v in vehicles:
        t = threading.Thread(
            target=vehicle_update_worker,
            name=f"vehicle-updater-{v.id}",
            args=(v, locks[v.id], stop_event, interval_sec),
            daemon=True,
        )
        t.start()
        threads.append(t)
    return threads, stop_event


# ----------------------------------------------------------------------------
# Thread-safe aggregations (consistent reads)
# ----------------------------------------------------------------------------
def compute_averages_threadsafe(fleet: FleetManager, locks: Dict[str, threading.Lock]) -> Tuple[float | None, float | None, float | None]:
    """Compute averages while holding all vehicle locks to ensure consistency."""
    if not fleet.vehicles:
        return None, None, None
    acquire_all_vehicle_locks(fleet.vehicles, locks)
    try:
        return fleet.average_speed(), fleet.average_temperature(), fleet.average_fuel()
    finally:
        release_all_vehicle_locks(fleet.vehicles, locks)


def get_alerts_threadsafe(fleet: FleetManager, locks: Dict[str, threading.Lock]) -> List[dict]:
    """Get alerts while holding all vehicle locks for a consistent snapshot."""
    if not fleet.vehicles:
        return []
    acquire_all_vehicle_locks(fleet.vehicles, locks)
    try:
        return fleet.get_alerts()
    finally:
        release_all_vehicle_locks(fleet.vehicles, locks)


# ----------------------------------------------------------------------------
# Benchmarks
# ----------------------------------------------------------------------------
def run_single_threaded(
    fleet: FleetManager,
    locks: Dict[str, threading.Lock],
    iterations: int,
    interval_sec: float,
) -> float:
    """Sequentially update all vehicles per iteration and compute stats.

    Returns elapsed seconds. Uses same update logic as threaded writers but
    runs in a single thread for fair comparison.
    """
    start = time.perf_counter()
    for _ in range(iterations):
        for v in fleet.vehicles:
            update_vehicle_once(v, locks[v.id])
        # Simulate telemetry tick
        time.sleep(interval_sec)
        _ = compute_averages_threadsafe(fleet, locks)
        _ = get_alerts_threadsafe(fleet, locks)
    return time.perf_counter() - start


def run_multi_threaded(
    fleet: FleetManager,
    locks: Dict[str, threading.Lock],
    iterations: int,
    interval_sec: float,
) -> float:
    """Spawn one writer thread per vehicle and compute stats concurrently.

    Returns elapsed seconds.
    """
    threads, stop_event = start_vehicle_update_threads(fleet.vehicles, locks, interval_sec)
    start = time.perf_counter()
    try:
        for _ in range(iterations):
            # Wait one tick between reads to let writers progress
            time.sleep(interval_sec)
            _ = compute_averages_threadsafe(fleet, locks)
            _ = get_alerts_threadsafe(fleet, locks)
    finally:
        # Signal writers to stop and wait for clean shutdown
        stop_event.set()
        for t in threads:
            t.join(timeout=interval_sec * 2)
    return time.perf_counter() - start


# ----------------------------------------------------------------------------
# CLI / Demonstration
# ----------------------------------------------------------------------------
def clone_vehicles(vehicles: List[Vehicle]) -> List[Vehicle]:
    """Create deep-ish clones of Vehicles to avoid cross-run interference."""
    return [Vehicle(v.id, v.speed, v.temperature, v.fuel) for v in vehicles]


def demo(csv_path: str, iterations: int, interval_sec: float) -> None:
    """Load vehicles, run single-threaded vs multi-threaded simulations, and print outputs."""
    vehicles = main_module.load_vehicles_from_csv(csv_path)
    if not vehicles:
        print("No vehicles to simulate.")
        return

    # Single-threaded run
    fleet_single = FleetManager(clone_vehicles(vehicles))
    locks_single = create_per_vehicle_locks(fleet_single.vehicles)
    single_elapsed = run_single_threaded(fleet_single, locks_single, iterations, interval_sec)
    s_speed, s_temp, s_fuel = compute_averages_threadsafe(fleet_single, locks_single)
    s_alerts = get_alerts_threadsafe(fleet_single, locks_single)

    # Multi-threaded run
    fleet_multi = FleetManager(clone_vehicles(vehicles))
    locks_multi = create_per_vehicle_locks(fleet_multi.vehicles)
    multi_elapsed = run_multi_threaded(fleet_multi, locks_multi, iterations, interval_sec)
    m_speed, m_temp, m_fuel = compute_averages_threadsafe(fleet_multi, locks_multi)
    m_alerts = get_alerts_threadsafe(fleet_multi, locks_multi)

    # Report
    print("Concurrent Telemetry Simulation\n" + "=" * 32)
    print(f"Vehicles: {len(vehicles)} | Iterations: {iterations} | Interval: {interval_sec:.3f}s")

    print("\nSingle-threaded (sequential updates):")
    print(f"  Elapsed: {single_elapsed:.3f}s")
    print(f"  Averages -> Speed: {s_speed if s_speed is not None else 'N/A':>6} km/h, "
          f"Temp: {s_temp if s_temp is not None else 'N/A':>6} °C, Fuel: {s_fuel if s_fuel is not None else 'N/A':>6} %")
    if s_alerts:
        for a in s_alerts:
            print(f"  Alert: Vehicle {a['id']}: {a['alert']}")
    else:
        print("  Alerts: None")

    print("\nMulti-threaded (1 thread per vehicle):")
    print(f"  Elapsed: {multi_elapsed:.3f}s")
    print(f"  Averages -> Speed: {m_speed if m_speed is not None else 'N/A':>6} km/h, "
          f"Temp: {m_temp if m_temp is not None else 'N/A':>6} °C, Fuel: {m_fuel if m_fuel is not None else 'N/A':>6} %")
    if m_alerts:
        for a in m_alerts:
            print(f"  Alert: Vehicle {a['id']}: {a['alert']}")
    else:
        print("  Alerts: None")

    if multi_elapsed < single_elapsed:
        print(f"\nSpeedup: {single_elapsed / multi_elapsed:.2f}x faster (multi-threaded vs single-threaded)")
    else:
        print("\nNote: Due to Python's GIL and I/O timing, multi-threading may not always be faster.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concurrent Fleet Telemetry Simulation")
    parser.add_argument("csv", help="Path to CSV file (id,speed,temperature,fuel)")
    parser.add_argument("--iterations", type=int, default=5, help="Number of read/update cycles")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between updates/reads")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    demo(args.csv, args.iterations, args.interval)


