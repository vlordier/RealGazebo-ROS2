"""Edge-case tests for drone_controller."""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import types
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ── Mock ROS2 modules ───────────────────────────────────────────────────────

mock_rclpy = types.ModuleType('rclpy')
mock_rclpy.node = types.ModuleType('rclpy.node')
mock_rclpy.qos = types.ModuleType('rclpy.qos')
mock_rclpy.clock = types.ModuleType('rclpy.clock')
mock_rclpy.parameter = types.ModuleType('rclpy.parameter')


class MockNode:
    def __init__(self, *a, **kw):
        self._publishers = {}
        self._subscriptions = []
        self._timers = []
    def declare_parameter(self, n, v): pass
    def get_parameter(self, n):
        m = MagicMock()
        m.get_parameter_value.return_value.integer_value = 1
        return m
    def create_subscription(self, *a, **kw): return MagicMock()
    def create_publisher(self, *a, **kw): return MagicMock()
    def create_timer(self, *a, **kw): return MagicMock()
    def get_logger(self): return MagicMock()
    def destroy_node(self): pass

mock_rclpy.node.Node = MockNode
mock_rclpy.qos.qos_profile_sensor_data = type('QoS', (), {})()
mock_rclpy.init = MagicMock()
mock_rclpy.spin_once = MagicMock()
mock_rclpy.shutdown = MagicMock()
mock_rclpy.ok = MagicMock(return_value=True)

mock_px4_msgs = types.ModuleType('px4_msgs')
mock_px4_msgs.msg = types.ModuleType('px4_msgs.msg')
mock_std_msgs = types.ModuleType('std_msgs')
mock_std_msgs.msg = types.ModuleType('std_msgs.msg')

sys.modules['rclpy'] = mock_rclpy
sys.modules['rclpy.node'] = mock_rclpy.node
sys.modules['rclpy.qos'] = mock_rclpy.qos
sys.modules['rclpy.clock'] = mock_rclpy.clock
sys.modules['rclpy.parameter'] = mock_rclpy.parameter
sys.modules['px4_msgs'] = mock_px4_msgs
sys.modules['px4_msgs.msg'] = mock_px4_msgs.msg
sys.modules['std_msgs'] = mock_std_msgs
sys.modules['std_msgs.msg'] = mock_std_msgs.msg


class MockVehicleStatus:
    ARMING_STATE_ARMED = 1
    ARMING_STATE_DISARMED = 0
    ARMING_STATE_INITED = 2
    ARMING_STATE_STANDBY = 3
    def __init__(self, nav=14, arm=1):
        self.nav_state = nav
        self.arming_state = arm


class MockVehicleCommand:
    VEHICLE_CMD_COMPONENT_ARM_DISARM = 400
    VEHICLE_CMD_NAV_TAKEOFF = 22
    VEHICLE_CMD_NAV_LAND = 21
    VEHICLE_CMD_DO_SET_MODE = 176
    def __init__(self):
        self.target_system = 0
        self.command = 0
        self.param1 = self.param2 = self.param3 = 0.0
        self.param4 = self.param5 = self.param6 = self.param7 = 0.0
        self.confirmation = False
        self.from_external = False


class MockVehicleLocalPosition:
    def __init__(self, x=0.0, y=0.0, z=-1.0, heading=0.0):
        self.x = x; self.y = y; self.z = z
        self.heading = heading
        self.timestamp = 0


class MockVehicleGlobalPosition:
    def __init__(self):
        self.lat = 36.728
        self.lon = 127.443
        self.alt = 68.9


class MockTrajectorySetpoint:
    def __init__(self):
        self.position = [0.0, 0.0, 0.0]
        self.yaw = 0.0


class MockOffboardControlMode:
    def __init__(self):
        self.position = True
        self.velocity = False
        self.acceleration = False
        self.attitude = False
        self.body_rate = False
        self.direct_actuator = False


for name, cls in [
    ("LogMessage", MagicMock), ("VehicleStatus", MockVehicleStatus),
    ("OffboardControlMode", MockOffboardControlMode),
    ("TrajectorySetpoint", MockTrajectorySetpoint),
    ("VehicleCommandAck", MagicMock), ("VehicleCommand", MockVehicleCommand),
    ("VehicleLocalPosition", MockVehicleLocalPosition),
    ("VehicleGlobalPosition", MockVehicleGlobalPosition),
]:
    setattr(mock_px4_msgs.msg, name, cls)

mock_std_msgs.msg.String = MagicMock

from drone_controller.drone_controller import (
    DroneController, NavState, MissionTick,
    TAKEOFF_ALTITUDE_M, MOVE_DISTANCE_NORTH_M,
    POSITION_REACHED_THRESHOLD_M, CONTROL_LOOP_PERIOD_S,
    PX4_CUSTOM_MAIN_MODE_OFFBOARD,
)


class TestConstants(unittest.TestCase):
    """Verify all named constants are defined and have sane values."""

    def test_mission_tick_order(self):
        self.assertLess(MissionTick.ARM, MissionTick.TAKEOFF)
        self.assertLess(MissionTick.TAKEOFF, MissionTick.OFFBOARD)
        self.assertLess(MissionTick.OFFBOARD, MissionTick.MOVE)

    def test_takeoff_altitude_positive(self):
        self.assertGreater(TAKEOFF_ALTITUDE_M, 0)

    def test_move_distance_positive(self):
        self.assertGreater(MOVE_DISTANCE_NORTH_M, 0)

    def test_position_threshold_positive(self):
        self.assertGreater(POSITION_REACHED_THRESHOLD_M, 0)

    def test_control_loop_period_sane(self):
        self.assertGreater(CONTROL_LOOP_PERIOD_S, 0)
        self.assertLess(CONTROL_LOOP_PERIOD_S, 1.0)

    def test_offboard_mode_code(self):
        self.assertEqual(PX4_CUSTOM_MAIN_MODE_OFFBOARD, 6.0)


class TestNavStateEnum(unittest.TestCase):
    """Verify all NavState values."""

    def test_all_values_defined(self):
        expected = {
            "MANUAL": 0, "ALTCTL": 1, "POSCTL": 2, "AUTO_MISSION": 3,
            "AUTO_LOITER": 4, "AUTO_RTL": 5, "OFFBOARD": 14,
            "AUTO_TAKEOFF": 17, "AUTO_LAND": 18, "ORBIT": 21,
        }
        for name, val in expected.items():
            self.assertEqual(NavState[name].value, val, f"{name}={val}")

    def test_no_duplicate_values(self):
        values = [e.value for e in NavState]
        self.assertEqual(len(values), len(set(values)))

    def test_all_names_uppercase(self):
        for e in NavState:
            self.assertEqual(e.name, e.name.upper())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        with patch('drone_controller.drone_controller.rclpy'), \
             patch('drone_controller.drone_controller.Node'), \
             patch('drone_controller.drone_controller.os'):
            self.controller = DroneController()

    def test_initial_setpoint_is_zero(self):
        self.assertEqual(self.controller.setpoint, [0.0, 0.0, 0.0])

    def test_setpoint_without_heading(self):
        with patch.object(self.controller, 'traj_setpoint_publisher_') as pub:
            self.controller.control_setpoint(10.0, 20.0, -5.0)
            setpoint = pub.publish.call_args[0][0]
            self.assertEqual(setpoint.position[0], 10.0)
            self.assertEqual(setpoint.position[1], 20.0)
            self.assertEqual(setpoint.position[2], -5.0)

    def test_setpoint_with_heading(self):
        with patch.object(self.controller, 'traj_setpoint_publisher_') as pub:
            self.controller.control_setpoint(1.0, 2.0, -3.0, heading=1.57)
            setpoint = pub.publish.call_args[0][0]
            self.assertEqual(setpoint.yaw, 1.57)

    def test_zero_distance_does_not_trigger_land(self):
        """At MISSION_TICK_MOVE+1 but far from setpoint, should NOT land."""
        self.controller.info_count = MissionTick.MOVE + 1
        self.controller.setpoint = [100.0, 100.0, -5.0]
        self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition(x=0, y=0, z=-1)
        with patch.object(self.controller, 'control_land') as land:
            self.controller.timer_display_info_callback()
            land.assert_not_called()

    def test_exact_setpoint_triggers_land(self):
        """At setpoint within threshold, should land."""
        self.controller.info_count = MissionTick.MOVE + 1
        self.controller.setpoint = [0.0, 0.0, -1.0]
        self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition(x=0, y=0, z=-1)
        with patch.object(self.controller, 'control_land') as land:
            self.controller.timer_display_info_callback()
            land.assert_called_once()

    def test_mission_skips_if_ticks_out_of_order(self):
        """Mission should only trigger at exact tick counts."""
        with patch.object(self.controller, 'control_arm') as arm, \
             patch.object(self.controller, 'control_takeoff') as takeoff:
            self.controller.info_count = MissionTick.ARM - 1
            self.controller.vehicle_status_msg_ = MockVehicleStatus()
            self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition()
            self.controller.timer_display_info_callback()
            arm.assert_called_once()  # 49 -> 50 -> arm

            self.controller.info_count = MissionTick.TAKEOFF - 1
            self.controller.timer_display_info_callback()
            takeoff.assert_called_once()  # 54 -> 55 -> takeoff

    def test_last_command_updates(self):
        self.controller.last_command = "idle"
        self.controller.control_arm()
        self.assertEqual(self.controller.last_command, "arm")
        self.controller.control_takeoff(10)
        self.assertEqual(self.controller.last_command, "takeoff")
        self.controller.control_offboard()
        self.assertEqual(self.controller.last_command, "offboard")
        self.controller.control_setpoint(0, 0, 0)
        self.assertEqual(self.controller.last_command, "move")
        self.controller.control_land()
        self.assertEqual(self.controller.last_command, "land")


if __name__ == '__main__':
    unittest.main()
