"""Tests for dora data model and operators."""

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2-bridge'))

from ros2_bridge.datamodel import VehiclePose, SimulationClock, VehicleStatus, V2VQuality


class TestVehiclePose(unittest.TestCase):
    def test_defaults(self):
        p = VehiclePose()
        self.assertEqual(p.x, 0.0)
        self.assertEqual(p.y, 0.0)
        self.assertEqual(p.z, 0.0)
        self.assertEqual(p.vehicle_id, 0)
        self.assertEqual(p.vehicle_type, "unknown")

    def test_custom_values(self):
        p = VehiclePose(x=10.5, y=20.3, z=-5.0, vehicle_id=1, vehicle_type="x500", heading=1.57)
        self.assertEqual(p.x, 10.5)
        self.assertEqual(p.y, 20.3)
        self.assertEqual(p.z, -5.0)
        self.assertEqual(p.vehicle_id, 1)
        self.assertEqual(p.vehicle_type, "x500")
        self.assertEqual(p.heading, 1.57)

    def test_to_json_roundtrip(self):
        p1 = VehiclePose(x=1.0, y=2.0, z=-3.0, vehicle_id=0, vehicle_type="x500", timestamp_us=1000)
        data = p1.to_json()
        p2 = VehiclePose.from_json(data)
        self.assertEqual(p1.x, p2.x)
        self.assertEqual(p1.y, p2.y)
        self.assertEqual(p1.z, p2.z)
        self.assertEqual(p1.vehicle_id, p2.vehicle_id)
        self.assertEqual(p1.vehicle_type, p2.vehicle_type)

    def test_json_format(self):
        p = VehiclePose(x=1.0, y=2.0, z=3.0)
        parsed = json.loads(p.to_json().decode())
        self.assertIn("x", parsed)
        self.assertIn("y", parsed)
        self.assertIn("z", parsed)
        self.assertIn("vehicle_id", parsed)
        self.assertIn("vehicle_type", parsed)


class TestSimulationClock(unittest.TestCase):
    def test_sim_time_s(self):
        c = SimulationClock(sec=5, nsec=500_000_000)
        self.assertAlmostEqual(c.sim_time_s, 5.5)

    def test_speed_factor(self):
        c = SimulationClock(sec=10, nsec=0, real_sec=5, real_nsec=0)
        self.assertAlmostEqual(c.speed_factor, 2.0)


class TestVehicleStatus(unittest.TestCase):
    def test_defaults(self):
        s = VehicleStatus()
        self.assertFalse(s.armed)
        self.assertEqual(s.battery_pct, 100.0)
        self.assertEqual(s.flight_mode, "UNKNOWN")

    def test_to_json(self):
        s = VehicleStatus(armed=True, battery_pct=75.5, flight_mode="OFFBOARD", vehicle_id=0)
        data = json.loads(s.to_json().decode())
        self.assertTrue(data["armed"])
        self.assertEqual(data["battery_pct"], 75.5)
        self.assertEqual(data["flight_mode"], "OFFBOARD")


class TestV2VQuality(unittest.TestCase):
    def test_defaults(self):
        q = V2VQuality()
        self.assertEqual(q.rssi_dbm, 0.0)
        self.assertEqual(q.packet_loss_rate, 0.0)

    def test_roundtrip(self):
        q1 = V2VQuality(source_id=0, dest_id=1, distance_m=100.0, rssi_dbm=-75.0, packet_loss_rate=0.3, latency_ms=15.0, jitter_ms=5.0)
        data = q1.to_json()
        parsed = json.loads(data.decode())
        self.assertEqual(parsed["source_id"], 0)
        self.assertEqual(parsed["dest_id"], 1)
        self.assertAlmostEqual(parsed["rssi_dbm"], -75.0)
        self.assertAlmostEqual(parsed["packet_loss_rate"], 0.3)


if __name__ == '__main__':
    unittest.main()
