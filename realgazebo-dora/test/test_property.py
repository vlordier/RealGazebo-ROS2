"""Property-based tests for Pydantic v2 data models.

Uses hypothesis to generate random valid/invalid inputs and verify
that validation constraints are correctly enforced.
"""

import os
import sys
import unittest

from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2-bridge'))

from ros2_bridge.datamodel import (
    SimulationClock,
    V2VQuality,
    VehicleConfig,
    VehiclePose,
    VehicleStatus,
)

# ── Reusable strategies ──────────────────────────────────────────────────────

valid_vehicle_types = st.sampled_from(
    ["x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat", "unknown"]
)
valid_firmwares = st.sampled_from(["px4", "ardupilot"])
valid_flight_modes = st.sampled_from(
    ["MANUAL", "ALTCTL", "POSCTL", "AUTO", "OFFBOARD", "STAB", "UNKNOWN"]
)


class TestVehiclePoseProperty(unittest.TestCase):
    @given(
        x=st.floats(min_value=-1e6, max_value=1e6),
        y=st.floats(min_value=-1e6, max_value=1e6),
        z=st.floats(min_value=-100, max_value=100),
        heading=st.floats(min_value=-6.28, max_value=6.28),
        vehicle_id=st.integers(min_value=0, max_value=255),
        vehicle_type=valid_vehicle_types,
    )
    def test_valid_params(self, x, y, z, heading, vehicle_id, vehicle_type):
        p = VehiclePose(x=x, y=y, z=z, heading=heading,
                         vehicle_id=vehicle_id, vehicle_type=vehicle_type)
        self.assertEqual(p.x, x)
        self.assertEqual(p.y, y)

    @given(bad_type=st.text().filter(
        lambda t: t not in ["x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat", "unknown"]
    ))
    def test_invalid_type_rejected(self, bad_type):
        with self.assertRaises(Exception):
            VehiclePose(vehicle_type=bad_type)

    @given(bad_id=st.integers(min_value=256))
    def test_invalid_id_rejected(self, bad_id):
        with self.assertRaises(Exception):
            VehiclePose(vehicle_id=bad_id)


class TestSimulationClockProperty(unittest.TestCase):
    @given(
        sec=st.integers(min_value=0, max_value=1_000_000),
        nsec=st.integers(min_value=0, max_value=999_999_999),
    )
    def test_valid_clock(self, sec, nsec):
        c = SimulationClock(sec=sec, nsec=nsec)
        self.assertAlmostEqual(c.sim_time_s, sec + nsec / 1e9)

    @given(nsec=st.integers(min_value=1_000_000_000))
    def test_invalid_nsec_rejected(self, nsec):
        with self.assertRaises(Exception):
            SimulationClock(sec=0, nsec=nsec)


class TestVehicleStatusProperty(unittest.TestCase):
    @given(
        armed=st.booleans(),
        nav_state=st.integers(min_value=0, max_value=31),
        battery_pct=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        flight_mode=valid_flight_modes,
        vehicle_id=st.integers(min_value=0, max_value=255),
    )
    def test_valid(self, armed, nav_state, battery_pct, flight_mode, vehicle_id):
        s = VehicleStatus(
            armed=armed, nav_state=nav_state, battery_pct=battery_pct,
            flight_mode=flight_mode, vehicle_id=vehicle_id,
        )
        self.assertEqual(s.armed, armed)
        self.assertEqual(s.nav_state, nav_state)

    @given(bad_battery=st.floats(min_value=101, max_value=1e6))
    def test_battery_over_limit(self, bad_battery):
        with self.assertRaises(Exception):
            VehicleStatus(battery_pct=bad_battery)


class TestV2VQualityProperty(unittest.TestCase):
    @given(
        source_id=st.integers(min_value=0, max_value=255),
        dest_id=st.integers(min_value=0, max_value=255),
        distance_m=st.floats(min_value=0, max_value=1e6, allow_nan=False),
        rssi_dbm=st.floats(min_value=-120, max_value=0, allow_nan=False),
        packet_loss_rate=st.floats(min_value=0, max_value=1),
        latency_ms=st.floats(min_value=0, max_value=1e5, allow_nan=False),
    )
    def test_valid(self, source_id, dest_id, distance_m, rssi_dbm, packet_loss_rate, latency_ms):
        q = V2VQuality(
            source_id=source_id, dest_id=dest_id, distance_m=distance_m,
            rssi_dbm=rssi_dbm, packet_loss_rate=packet_loss_rate, latency_ms=latency_ms,
        )
        self.assertEqual(q.source_id, source_id)

    @given(bad_rssi=st.floats(min_value=0.1, max_value=100))
    def test_positive_rssi_rejected(self, bad_rssi):
        with self.assertRaises(Exception):
            V2VQuality(rssi_dbm=bad_rssi)


class TestVehicleConfigProperty(unittest.TestCase):
    @given(
        vtype=st.sampled_from(["x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat", "rock"]),
        firmware=st.sampled_from(["px4", "ardupilot"]),
        build=st.integers(min_value=0, max_value=10),
    )
    def test_valid(self, vtype, firmware, build):
        c = VehicleConfig(type=vtype, firmware=firmware, build_target=build)
        self.assertEqual(c.type, vtype)

    @given(bad_type=st.text().filter(
        lambda t: t not in {"x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat", "rock"}
    ))
    def test_invalid_type_rejected(self, bad_type):
        with self.assertRaises(Exception):
            VehicleConfig(type=bad_type)


if __name__ == '__main__':
    unittest.main()
