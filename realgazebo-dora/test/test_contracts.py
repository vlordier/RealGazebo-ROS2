"""Tests for the RealGazebo interface contract models.

Verifies that UE5 UDP packet encoding matches the C++ struct layout
from RealGazebo.cpp (header packed as <BBB, then 7 floats).
"""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ros2-bridge'))

from ros2_bridge.contracts import (
    PACKED_HEADER_FMT,
    MotorRPM,
    SimReset,
    VehiclePose,
    parse_ue5_packet,
)


class TestVehiclePoseContract(unittest.TestCase):
    """Test VehiclePose serialization matches C++ RealGazebo.cpp layout."""

    def test_ue5_packet_size(self):
        p = VehiclePose(x=1.0, y=2.0, z=-3.0, vehicle_num=0, vehicle_code=0)
        packet = p.to_ue5_packet()
        # C++ sends: sizeof(RealGazeboPacketHeader) + 7*sizeof(float)
        # = 3 + 28 = 31 bytes
        self.assertEqual(len(packet), 31)

    def test_ue5_packet_header(self):
        p = VehiclePose(x=0, y=0, z=0, vehicle_num=5, vehicle_code=3, qw=1.0)
        packet = p.to_ue5_packet()
        header = struct.unpack(PACKED_HEADER_FMT, packet[:3])
        self.assertEqual(header[0], 5)  # vehicle_num
        self.assertEqual(header[1], 3)  # vehicle_code
        self.assertEqual(header[2], 1)  # data_type = 1 (pose)

    def test_ue5_packet_pose_values(self):
        p = VehiclePose(x=10.5, y=-20.3, z=-5.0, qx=0.1, qy=0.2, qz=0.3, qw=0.9)
        packet = p.to_ue5_packet()
        values = struct.unpack("<7f", packet[3:31])
        self.assertAlmostEqual(values[0], 10.5, places=5)
        self.assertAlmostEqual(values[1], -20.3, places=5)
        self.assertAlmostEqual(values[2], -5.0, places=5)
        self.assertAlmostEqual(values[3], 0.1, places=5)
        self.assertAlmostEqual(values[4], 0.2, places=5)
        self.assertAlmostEqual(values[5], 0.3, places=5)
        self.assertAlmostEqual(values[6], 0.9, places=5)

    def test_roundtrip(self):
        p1 = VehiclePose(x=1.0, y=2.0, z=-3.0, qx=0.0, qy=0.0, qz=0.0, qw=1.0,
                          vehicle_num=0, vehicle_code=0)
        packet = p1.to_ue5_packet()
        p2 = VehiclePose.from_ue5_packet(packet)
        self.assertIsNotNone(p2)
        self.assertAlmostEqual(p2.x, p1.x)
        self.assertAlmostEqual(p2.y, p1.y)
        self.assertAlmostEqual(p2.z, p1.z)

    def test_from_invalid_packet(self):
        result = VehiclePose.from_ue5_packet(b"")
        self.assertIsNone(result)

    def test_parse_ue5_dispatcher(self):
        p = VehiclePose(x=0, y=0, z=0, vehicle_num=0, vehicle_code=0)
        parsed = parse_ue5_packet(p.to_ue5_packet())
        self.assertIsInstance(parsed, VehiclePose)


class TestMotorRPMContract(unittest.TestCase):
    def test_rpm_packet_header(self):
        r = MotorRPM(vehicle_num=1, vehicle_code=0, rpm_values=[100.0, 200.0])
        packet = r.to_ue5_packet()
        header = struct.unpack(PACKED_HEADER_FMT, packet[:3])
        self.assertEqual(header[0], 1)
        self.assertEqual(header[2], 2)  # data_type = 2 (RPM)

    def test_rpm_packet_values(self):
        r = MotorRPM(vehicle_num=0, vehicle_code=0, rpm_values=[1000.0, 2000.0, 3000.0, 4000.0])
        packet = r.to_ue5_packet()
        # Header (3) + 4 floats (16) = 19 bytes
        self.assertEqual(len(packet), 19)
        values = struct.unpack("<4f", packet[3:19])
        self.assertAlmostEqual(values[0], 1000.0)
        self.assertAlmostEqual(values[3], 4000.0)


class TestSimResetContract(unittest.TestCase):
    def test_reset_packet(self):
        r = SimReset(vehicle_num=2, vehicle_code=1)
        packet = r.to_ue5_packet()
        self.assertEqual(len(packet), 3)  # header only, no payload
        header = struct.unpack(PACKED_HEADER_FMT, packet)
        self.assertEqual(header[0], 2)
        self.assertEqual(header[1], 1)
        self.assertEqual(header[2], 4)  # data_type = 4 (reset)

    def test_parse_reset(self):
        r = SimReset(vehicle_num=0, vehicle_code=0)
        parsed = parse_ue5_packet(r.to_ue5_packet())
        self.assertIsInstance(parsed, SimReset)


class TestDataTypes(unittest.TestCase):
    def test_all_types_have_models(self):
        from ros2_bridge.contracts import UE5_DATA_TYPES
        for dtype, model in UE5_DATA_TYPES.items():
            with self.subTest(dtype=dtype):
                self.assertTrue(issubclass(model, VehiclePose) or
                                issubclass(model, (MotorRPM, SimReset)))


if __name__ == '__main__':
    unittest.main()
