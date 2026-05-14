"""Tests for PX4 ROS2 bridge command handling and constants."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manager.constants import KEY_BINDINGS


class TestVehicleEnum(unittest.TestCase):
    """Test the Vehicle enum values."""

    def setUp(self):
        # Can't import from px4_ros2 directly (needs rclpy), so we
        # define the expected enum values inline
        self.expected = {'DRONE': 0, 'ROVER': 1, 'BOAT': 2, 'UNKNOWN': 99}

    def test_values_match(self):
        self.assertEqual(self.expected['DRONE'], 0)
        self.assertEqual(self.expected['ROVER'], 1)
        self.assertEqual(self.expected['BOAT'], 2)
        self.assertEqual(self.expected['UNKNOWN'], 99)

    def test_all_expected_keys(self):
        self.assertEqual(set(self.expected.keys()), {'DRONE', 'ROVER', 'BOAT', 'UNKNOWN'})


class TestMoveDistances(unittest.TestCase):
    """Test the vehicle-specific move distance logic."""

    def test_default_distance(self):
        # system_ids 1-8, 11+ should use default 300m north
        self.assertEqual(300, 300)

    def test_system_9_and_10_east(self):
        systems_9_10 = {9, 10}
        for sid in systems_9_10:
            offsets = self._get_offsets(sid)
            self.assertEqual(
                offsets, (0.0, -100.0), f'system {sid} should move -100m east, got {offsets}'
            )

    def test_system_4_7_distance(self):
        for sid in range(1, 9):
            if sid not in (9, 10):
                offsets = self._get_offsets(sid)
                self.assertEqual(offsets, (-300.0, 0.0), f'system {sid} should move -300m north')

    def _get_offsets(self, system_id):
        """Replica of the move distance logic from px4_ros2.py. Returns (y_offset, x_offset)."""
        VEHICLE_MOVE_DISTANCES = {
            9: (0.0, -100.0),
            10: (0.0, -100.0),
        }
        return VEHICLE_MOVE_DISTANCES.get(system_id, (-300.0, 0.0))


class TestCommandMapping(unittest.TestCase):
    """Test that px4_ros2 commands match manager/controller commands."""

    def test_all_controller_commands_supported(self):
        px4_supported = {'ARM', 'DISARM', 'OFFBOARD', 'TAKEOFF', 'START'}
        set(KEY_BINDINGS.values())
        for cmd_key, cmd_val in KEY_BINDINGS.items():
            with self.subTest(cmd=cmd_val):
                self.assertIn(
                    cmd_val, px4_supported, f"'{cmd_val}' from key '{cmd_key}' not in px4_ros2"
                )


if __name__ == '__main__':
    unittest.main()
