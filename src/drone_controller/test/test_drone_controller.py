"""Tests for drone_controller mission logic.

Tests the control methods by mocking ROS2 dependencies.
To run: python3 -m pytest src/drone_controller/test/ -v
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Create proper mock module hierarchy for rclpy
mock_rclpy = types.ModuleType('rclpy')
mock_rclpy.node = types.ModuleType('rclpy.node')
mock_rclpy.qos = types.ModuleType('rclpy.qos')
mock_rclpy.clock = types.ModuleType('rclpy.clock')

class MockNode:
    def __init__(self, *a, **kw):
        self._publishers = {}
        self._subscriptions = []
        self._timers = []
    def declare_parameter(self, n, v): pass
    def get_parameter(self, n): return MagicMock()
    def create_subscription(self, *a, **kw): return MagicMock()
    def create_publisher(self, *a, **kw): return MagicMock()
    def create_timer(self, *a, **kw): return MagicMock()
    def get_logger(self): return MagicMock()
    def destroy_node(self): pass

mock_rclpy.node.Node = MockNode

class MockQoSProfile: pass
mock_rclpy.qos.qos_profile_sensor_data = MockQoSProfile()
mock_rclpy.init = MagicMock()
mock_rclpy.spin_once = MagicMock()
mock_rclpy.shutdown = MagicMock()
mock_rclpy.ok = MagicMock(return_value=True)

# Mock px4_msgs and std_msgs
mock_px4_msgs = types.ModuleType('px4_msgs')
mock_px4_msgs.msg = types.ModuleType('px4_msgs.msg')
mock_std_msgs = types.ModuleType('std_msgs')
mock_std_msgs.msg = types.ModuleType('std_msgs.msg')

sys.modules['rclpy'] = mock_rclpy
sys.modules['rclpy.node'] = mock_rclpy.node
sys.modules['rclpy.qos'] = mock_rclpy.qos
sys.modules['rclpy.clock'] = mock_rclpy.clock
sys.modules['px4_msgs'] = mock_px4_msgs
sys.modules['px4_msgs.msg'] = mock_px4_msgs.msg
sys.modules['std_msgs'] = mock_std_msgs
sys.modules['std_msgs.msg'] = mock_std_msgs.msg

# Now set up the message types on the mocks before importing drone_controller
from unittest.mock import MagicMock


class MockVehicleStatus:
    ARMING_STATE_ARMED = 1
    ARMING_STATE_DISARMED = 0
    def __init__(self):
        self.nav_state = 14
        self.arming_state = self.ARMING_STATE_ARMED

class MockVehicleCommand:
    VEHICLE_CMD_COMPONENT_ARM_DISARM = 400
    VEHICLE_CMD_NAV_TAKEOFF = 22
    VEHICLE_CMD_NAV_LAND = 21
    VEHICLE_CMD_DO_SET_MODE = 176
    def __init__(self):
        self.target_system = 0; self.command = 0
        self.param1 = 0.0; self.param2 = 0.0; self.param3 = 0.0
        self.param4 = 0.0; self.param5 = 0.0; self.param6 = 0.0
        self.param7 = 0.0; self.confirmation = False; self.from_external = False

class MockVehicleLocalPosition:
    def __init__(self, x=0.0, y=0.0, z=-1.0, heading=0.0):
        self.x = x; self.y = y; self.z = z; self.heading = heading; self.timestamp = 0

class MockVehicleGlobalPosition:
    def __init__(self):
        self.lat = 36.728; self.lon = 127.443; self.alt = 68.9

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

for name, cls in [("LogMessage", MagicMock), ("VehicleStatus", MockVehicleStatus),
                   ("OffboardControlMode", MockOffboardControlMode),
                   ("TrajectorySetpoint", MockTrajectorySetpoint),
                   ("VehicleCommandAck", MagicMock), ("VehicleCommand", MockVehicleCommand),
                   ("VehicleLocalPosition", MockVehicleLocalPosition),
                   ("VehicleGlobalPosition", MockVehicleGlobalPosition)]:
    setattr(mock_px4_msgs.msg, name, cls)

mock_std_msgs.msg.String = MagicMock

from drone_controller.drone_controller import (
    DroneController,
    NavState,
)


class TestDroneController(unittest.TestCase):
    """Test drone controller control methods"""

    def setUp(self):
        with patch('drone_controller.drone_controller.rclpy'), \
             patch('drone_controller.drone_controller.Node'), \
             patch('drone_controller.drone_controller.os'):
            self.controller = DroneController()

    def test_initialization(self):
        self.assertEqual(self.controller.last_command, "idle")
        self.assertEqual(self.controller.info_count, 0)
        self.assertEqual(self.controller.setpoint, [0, 0, 0])

    def test_nav_state_enum(self):
        self.assertEqual(NavState.MANUAL.value, 0)
        self.assertEqual(NavState.OFFBOARD.value, 14)
        self.assertEqual(NavState.AUTO_TAKEOFF.value, 17)
        self.assertEqual(NavState.AUTO_LAND.value, 18)

    def test_control_arm(self):
        with patch.object(self.controller, 'vehicle_command_publisher_') as pub:
            self.controller.system_id_ = 1
            self.controller.control_arm()
            self.assertEqual(self.controller.last_command, "arm")
            pub.publish.assert_called_once()
            cmd = pub.publish.call_args[0][0]
            self.assertEqual(cmd.target_system, 1)
            self.assertEqual(cmd.command, MockVehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM)
            self.assertEqual(cmd.param1, 1.0)

    def test_control_disarm(self):
        with patch.object(self.controller, 'vehicle_command_publisher_') as pub:
            self.controller.control_disarm()
            self.assertEqual(self.controller.last_command, "disarm")
            cmd = pub.publish.call_args[0][0]
            self.assertEqual(cmd.param1, 0.0)

    def test_control_takeoff(self):
        with patch.object(self.controller, 'vehicle_command_publisher_') as pub:
            self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition()
            self.controller.vehicle_global_position_msg_ = MockVehicleGlobalPosition()
            self.controller.control_takeoff(5)
            self.assertEqual(self.controller.last_command, "takeoff")
            cmd = pub.publish.call_args[0][0]
            self.assertEqual(cmd.command, MockVehicleCommand.VEHICLE_CMD_NAV_TAKEOFF)
            self.assertEqual(cmd.param7, 68.9 + 5)  # alt + 5

    def test_control_offboard(self):
        with patch.object(self.controller, 'vehicle_command_publisher_') as pub:
            self.controller.control_offboard()
            self.assertEqual(self.controller.last_command, "offboard")
            cmd = pub.publish.call_args[0][0]
            self.assertEqual(cmd.command, MockVehicleCommand.VEHICLE_CMD_DO_SET_MODE)
            self.assertEqual(cmd.param1, 1.0)
            self.assertEqual(cmd.param2, 6.0)  # PX4_CUSTOM_MAIN_MODE_OFFBOARD

    def test_control_land(self):
        with patch.object(self.controller, 'vehicle_command_publisher_') as pub:
            self.controller.control_land()
            self.assertEqual(self.controller.last_command, "land")
            cmd = pub.publish.call_args[0][0]
            self.assertEqual(cmd.command, MockVehicleCommand.VEHICLE_CMD_NAV_LAND)

    def test_control_setpoint(self):
        with patch.object(self.controller, 'traj_setpoint_publisher_') as pub:
            self.controller.control_setpoint(10.0, 20.0, -5.0, heading=1.57)
            setpoint = pub.publish.call_args[0][0]
            self.assertEqual(setpoint.position[0], 10.0)
            self.assertEqual(setpoint.position[1], 20.0)
            self.assertEqual(setpoint.position[2], -5.0)
            self.assertEqual(setpoint.yaw, 1.57)

    def test_mission_sequence(self):
        """Test the automated mission sequence"""
        self.controller.vehicle_status_msg_ = MockVehicleStatus()
        self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition(x=0, y=0, z=-1)

        with patch.object(self.controller, 'control_arm') as arm, \
             patch.object(self.controller, 'control_takeoff') as takeoff, \
             patch.object(self.controller, 'control_offboard') as offboard, \
             patch.object(self.controller, 'control_setpoint') as setpoint, \
             patch.object(self.controller, 'control_land') as land:

            # Simulate mission progression
            self.controller.vehicle_status_msg_ = MockVehicleStatus()
            self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition(x=0, y=0, z=-5, heading=0)

            # info_count = 49 -> becomes 50 after increment -> arm
            self.controller.info_count = 49
            self.controller.timer_display_info_callback()
            arm.assert_called_once()

            # info_count = 54 -> becomes 55 after increment -> takeoff
            self.controller.info_count = 54
            self.controller.timer_display_info_callback()
            takeoff.assert_called_once_with(5)

            # info_count = 144 -> becomes 145 -> offboard
            self.controller.info_count = 144
            self.controller.timer_display_info_callback()
            offboard.assert_called_once()

            # info_count = 154 -> becomes 155 -> setpoint
            self.controller.info_count = 154
            self.controller.timer_display_info_callback()
            setpoint.assert_called_once()

            # info_count > 155 and position close -> land
            self.controller.info_count = 199  # becomes 200
            self.controller.setpoint = [0, -50, -5]
            self.controller.vehicle_local_position_msg_ = MockVehicleLocalPosition(x=0, y=-49.5, z=-5)
            self.controller.timer_display_info_callback()
            land.assert_called_once()


if __name__ == '__main__':
    unittest.main()
