"""Tests for Pydantic v2 data models with field validation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2-bridge'))

from ros2_bridge.datamodel import (
    SimulationClock,
    V2VQuality,
    VehicleConfig,
    VehiclePose,
    VehicleStatus,
)


class TestVehiclePoseValidation(unittest.TestCase):
    """Test Pydantic field validation on VehiclePose."""

    def test_defaults(self):
        p = VehiclePose()
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.vehicle_type, "unknown")
        self.assertEqual(p.vehicle_id, 0)

    def test_valid_values(self):
        p = VehiclePose(x=10.5, y=-20.3, z=-5.0, vehicle_id=1, vehicle_type="x500")
        self.assertEqual(p.x, 10.5)
        self.assertEqual(p.y, -20.3)
        self.assertEqual(p.z, -5.0)

    def test_vehicle_type_regex(self):
        valid = ["x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat", "unknown"]
        for vt in valid:
            p = VehiclePose(vehicle_type=vt)
            self.assertEqual(p.vehicle_type, vt)

    def test_invalid_vehicle_type(self):
        with self.assertRaises(Exception):
            VehiclePose(vehicle_type="spaceship")

    def test_vehicle_id_range(self):
        VehiclePose(vehicle_id=0)
        VehiclePose(vehicle_id=255)
        with self.assertRaises(Exception):
            VehiclePose(vehicle_id=-1)
        with self.assertRaises(Exception):
            VehiclePose(vehicle_id=256)

    def test_heading_range(self):
        VehiclePose(heading=0.0)
        VehiclePose(heading=3.14)
        VehiclePose(heading=-3.14)
        with self.assertRaises(Exception):
            VehiclePose(heading=10.0)

    def test_z_validator_large_positive(self):
        with self.assertRaises(Exception):
            VehiclePose(z=500.0)

    def test_to_json_roundtrip(self):
        p1 = VehiclePose(x=1.0, y=2.0, z=-3.0, vehicle_type="x500", vehicle_id=0, timestamp_us=1000)
        data = p1.to_json()
        p2 = VehiclePose.from_json(data)
        assert p1 == p2

    def test_json_contains_all_fields(self):
        p = VehiclePose(x=1.0, y=2.0, z=-3.0)
        raw = p.model_dump_json()
        for field in ("x", "y", "z", "vehicle_id", "vehicle_type", "heading", "timestamp_us"):
            self.assertIn(field, raw)


class TestSimulationClock(unittest.TestCase):
    """Test SimulationClock properties and validation."""

    def test_sim_time_s_property(self):
        c = SimulationClock(sec=5, nsec=500_000_000)
        self.assertAlmostEqual(c.sim_time_s, 5.5)

    def test_speed_factor(self):
        c = SimulationClock(sec=10, real_sec=5)
        self.assertAlmostEqual(c.speed_factor, 2.0)

    def test_zero_real_time(self):
        c = SimulationClock(sec=0, real_sec=0)
        self.assertEqual(c.speed_factor, 1.0)

    def test_nsec_range(self):
        with self.assertRaises(Exception):
            SimulationClock(sec=0, nsec=1_500_000_000)
        with self.assertRaises(Exception):
            SimulationClock(sec=0, nsec=-1)


class TestVehicleStatus(unittest.TestCase):
    """Test VehicleStatus field validation."""

    def test_battery_range(self):
        VehicleStatus(battery_pct=50.0)
        VehicleStatus(battery_pct=0.0)
        VehicleStatus(battery_pct=100.0)
        with self.assertRaises(Exception):
            VehicleStatus(battery_pct=-1.0)
        with self.assertRaises(Exception):
            VehicleStatus(battery_pct=101.0)

    def test_nav_state_range(self):
        VehicleStatus(nav_state=0)
        VehicleStatus(nav_state=31)
        with self.assertRaises(Exception):
            VehicleStatus(nav_state=32)

    def test_flight_mode_normalization(self):
        s = VehicleStatus(flight_mode="offboard")
        self.assertEqual(s.flight_mode, "OFFBOARD")

    def test_invalid_flight_mode(self):
        with self.assertRaises(Exception):
            VehicleStatus(flight_mode="HYPERDRIVE")

    def test_to_json(self):
        s = VehicleStatus(armed=True, battery_pct=75.5, flight_mode="OFFBOARD")
        data = s.to_json()
        self.assertIn(b'"armed":true', data)
        self.assertIn(b'"battery_pct":75.5', data)


class TestV2VQuality(unittest.TestCase):
    """Test V2VQuality field validation."""

    def test_defaults(self):
        q = V2VQuality()
        self.assertEqual(q.rssi_dbm, 0.0)
        self.assertEqual(q.packet_loss_rate, 0.0)

    def test_packet_loss_range(self):
        V2VQuality(packet_loss_rate=0.0)
        V2VQuality(packet_loss_rate=1.0)
        with self.assertRaises(Exception):
            V2VQuality(packet_loss_rate=-0.1)
        with self.assertRaises(Exception):
            V2VQuality(packet_loss_rate=1.1)

    def test_rssi_must_be_non_positive(self):
        V2VQuality(rssi_dbm=-60.0)
        V2VQuality(rssi_dbm=0.0)
        with self.assertRaises(Exception):
            V2VQuality(rssi_dbm=10.0)

    def test_latency_range(self):
        V2VQuality(latency_ms=0.0)
        V2VQuality(latency_ms=1e5)
        with self.assertRaises(Exception):
            V2VQuality(latency_ms=-1.0)

    def test_distance_range(self):
        V2VQuality(distance_m=0.0)
        V2VQuality(distance_m=1e6)
        with self.assertRaises(Exception):
            V2VQuality(distance_m=-1.0)

    def test_roundtrip(self):
        q1 = V2VQuality(
            source_id=0, dest_id=1, distance_m=100.0,
            rssi_dbm=-75.0, packet_loss_rate=0.3,
            latency_ms=15.0, jitter_ms=5.0
        )
        data = q1.to_json()
        q2 = V2VQuality.model_validate_json(data.decode())
        assert q1 == q2


class TestVehicleConfig(unittest.TestCase):
    """Test VehicleConfig for YAML validation."""

    def test_px4_firmware_default(self):
        c = VehicleConfig(type="x500")
        self.assertEqual(c.firmware, "px4")

    def test_ardupilot_firmware(self):
        c = VehicleConfig(type="x500", firmware="ardupilot")
        self.assertEqual(c.firmware, "ardupilot")

    def test_invalid_firmware(self):
        with self.assertRaises(Exception):
            VehicleConfig(type="x500", firmware="crazyflie")

    def test_valid_types(self):
        for vt in ["x500", "x500_lidar_2d", "lc_62", "rover_ackermann", "boat"]:
            c = VehicleConfig(type=vt)
            self.assertEqual(c.type, vt)

    def test_rock_type(self):
        c = VehicleConfig(type="rock")
        self.assertEqual(c.type, "rock")

    def test_invalid_type(self):
        with self.assertRaises(Exception):
            VehicleConfig(type="spaceship")

    def test_spawnpoint_default(self):
        c = VehicleConfig(type="x500")
        self.assertEqual(c.spawnpoint, (0.0, 0.0, 0.0, 0.0))

    def test_spawnpoint_yaw_validation(self):
        VehicleConfig(type="x500", spawnpoint=(0, 0, 0, 3.14))
        VehicleConfig(type="x500", spawnpoint=(0, 0, 0, -3.14))
        with self.assertRaises(Exception):
            VehicleConfig(type="x500", spawnpoint=(0, 0, 0, 10.0))


if __name__ == '__main__':
    unittest.main()
