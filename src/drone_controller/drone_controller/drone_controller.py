import math
import os
from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleGlobalPosition,
    VehicleLocalPosition,
    VehicleStatus,
)

# ── Nav State Enum ──────────────────────────────────────────────────────────


class NavState(Enum):
    MANUAL = 0
    ALTCTL = 1
    POSCTL = 2
    AUTO_MISSION = 3
    AUTO_LOITER = 4
    AUTO_RTL = 5
    POSITION_SLOW = 6
    ACRO = 10
    DESCEND = 12
    TERMINATION = 13
    OFFBOARD = 14
    STAB = 15
    AUTO_TAKEOFF = 17
    AUTO_LAND = 18
    AUTO_FOLLOW_TARGET = 19
    AUTO_PRECLAND = 20
    ORBIT = 21
    AUTO_VTOL_TAKEOFF = 22


# ── Mission Constants ───────────────────────────────────────────────────────

# ── Mission Timing Constants ────────────────────────────────────────────────


class MissionTick:
    ARM = 50
    TAKEOFF = 55
    OFFBOARD = 145
    MOVE = 155


TAKEOFF_ALTITUDE_M = 5.0
MOVE_DISTANCE_NORTH_M = 50.0
POSITION_REACHED_THRESHOLD_M = 1.0
CONTROL_LOOP_PERIOD_S = 0.1

PX4_CUSTOM_MAIN_MODE_OFFBOARD = 6.0

# ── Arming / Mode Constants (from PX4 definitions) ─────────────────────────

ARM_CONFIRM = 1.0
DISARM_PARAM = 0.0


class DroneController(Node):
    def __init__(self):
        super().__init__('drone_controller')
        self.initialize_node()

    def timer_display_info_callback(self):
        os.system('clear')
        nav = NavState(self.vehicle_status_msg_.nav_state)
        arm_state = (
            'ARM'
            if self.vehicle_status_msg_.arming_state == VehicleStatus.ARMING_STATE_ARMED
            else 'DISARM'
        )
        pos = self.vehicle_local_position_msg_
        self.get_logger().info(
            f'[dc] Mode={nav.name} {arm_state} '
            f'pos=({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f}) '
            f'cmd={self.last_command} tick={self.info_count}'
        )

        self.info_count += 1

        match self.info_count:
            case MissionTick.ARM:
                self.get_logger().info('[dc] Starting mission: ARM')
                self.control_arm()
            case MissionTick.TAKEOFF:
                self.get_logger().info(f'[dc] Takeoff to {TAKEOFF_ALTITUDE_M}m')
                self.control_takeoff(TAKEOFF_ALTITUDE_M)
            case MissionTick.OFFBOARD:
                self.get_logger().info('[dc] Switching to OFFBOARD mode')
                self.control_offboard()
            case MissionTick.MOVE:
                pos = self.vehicle_local_position_msg_
                self.setpoint = [pos.x, pos.y - MOVE_DISTANCE_NORTH_M, pos.z]
                self.get_logger().info(
                    f'[dc] Moving to setpoint ({self.setpoint[0]:.1f}, {self.setpoint[1]:.1f}, {self.setpoint[2]:.1f})'
                )
                self.control_setpoint(
                    self.setpoint[0],
                    self.setpoint[1],
                    self.setpoint[2],
                    self.vehicle_local_position_msg_.heading,
                )

        if self.info_count > MissionTick.MOVE:
            dx = self.setpoint[0] - self.vehicle_local_position_msg_.x
            dy = self.setpoint[1] - self.vehicle_local_position_msg_.y
            dz = self.setpoint[2] - self.vehicle_local_position_msg_.z
            distance = math.sqrt(dx * dx + dy * dy + dz * dz)
            if distance < POSITION_REACHED_THRESHOLD_M:
                self.get_logger().info(f'[dc] Setpoint reached, landing (dist={distance:.2f}m)')
                self.control_land()

    def vehicle_local_position_callback(self, msg):
        self.vehicle_local_position_msg_ = msg

    def vehicle_global_position_callback(self, msg):
        self.vehicle_global_position_msg_ = msg

    def vehicle_status_callback(self, msg):
        self.vehicle_status_msg_ = msg
        self.get_logger().debug(f'[dc] Status: nav_state={msg.nav_state} arming={msg.arming_state}')

    def timer_ocm_callback(self):
        self.ocm_publisher_.publish(self.ocm_msg_qhac_)

    def control_arm(self):
        self.last_command = 'arm'
        arm_cmd = VehicleCommand()
        arm_cmd.target_system = self.system_id_
        arm_cmd.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        arm_cmd.param1 = ARM_CONFIRM
        arm_cmd.confirmation = True
        arm_cmd.from_external = True
        self.vehicle_command_publisher_.publish(arm_cmd)
        self.get_logger().info(f'[dc] Arm command sent to system {self.system_id_}')

    def control_takeoff(self, altitude):
        self.last_command = 'takeoff'
        takeoff_cmd = VehicleCommand()
        takeoff_cmd.target_system = self.system_id_
        takeoff_cmd.command = VehicleCommand.VEHICLE_CMD_NAV_TAKEOFF
        takeoff_cmd.param1 = -1.0
        takeoff_cmd.param4 = self.vehicle_local_position_msg_.heading
        takeoff_cmd.param5 = self.vehicle_global_position_msg_.lat
        takeoff_cmd.param6 = self.vehicle_global_position_msg_.lon
        takeoff_cmd.param7 = self.vehicle_global_position_msg_.alt + altitude
        self.vehicle_command_publisher_.publish(takeoff_cmd)
        self.get_logger().info(f'[dc] Takeoff command: altitude={altitude:.1f}m')

    def control_disarm(self):
        self.last_command = 'disarm'
        disarm_cmd = VehicleCommand()
        disarm_cmd.target_system = self.system_id_
        disarm_cmd.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        disarm_cmd.param1 = DISARM_PARAM
        disarm_cmd.confirmation = True
        self.vehicle_command_publisher_.publish(disarm_cmd)

    def control_offboard(self):
        self.last_command = 'offboard'
        offboard_cmd = VehicleCommand()
        offboard_cmd.target_system = self.system_id_
        offboard_cmd.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
        offboard_cmd.param1 = 1.0
        offboard_cmd.param2 = PX4_CUSTOM_MAIN_MODE_OFFBOARD
        offboard_cmd.from_external = True
        self.vehicle_command_publisher_.publish(offboard_cmd)
        self.get_logger().info('[dc] Offboard mode command sent')

    def control_setpoint(self, x, y, z, heading=None):
        self.last_command = 'move'
        setpoint_cmd = TrajectorySetpoint()
        setpoint_cmd.position[0] = x
        setpoint_cmd.position[1] = y
        setpoint_cmd.position[2] = z
        if heading is not None:
            setpoint_cmd.yaw = heading
        self.traj_setpoint_publisher_.publish(setpoint_cmd)

    def control_land(self):
        self.last_command = 'land'
        landing_cmd = VehicleCommand()
        landing_cmd.target_system = self.system_id_
        landing_cmd.command = VehicleCommand.VEHICLE_CMD_NAV_LAND
        landing_cmd.from_external = True
        self.vehicle_command_publisher_.publish(landing_cmd)
        self.get_logger().info('[dc] Land command sent')

    def initialize_node(self):
        self.declare_parameter('system_id', 1)
        self.system_id_ = self.get_parameter('system_id').get_parameter_value().integer_value
        self.last_command = 'idle'

        self.get_logger().info(f'[dc] Initializing drone_controller for system {self.system_id_}')

        topic_prefix_fmu = f'vehicle{self.system_id_}/fmu/'

        self.vehicle_status_subscriber = self.create_subscription(
            VehicleStatus,
            f'{topic_prefix_fmu}out/vehicle_status',
            self.vehicle_status_callback,
            qos_profile_sensor_data,
        )
        self.vehicle_status_msg_ = VehicleStatus()

        self.ocm_msg_qhac_ = OffboardControlMode()
        self.ocm_msg_qhac_.position = True
        self.ocm_publisher_ = self.create_publisher(
            OffboardControlMode,
            f'{topic_prefix_fmu}in/offboard_control_mode',
            qos_profile_sensor_data,
        )

        self.traj_setpoint_publisher_ = self.create_publisher(
            TrajectorySetpoint, f'{topic_prefix_fmu}in/trajectory_setpoint', qos_profile_sensor_data
        )

        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand, f'{topic_prefix_fmu}in/vehicle_command', qos_profile_sensor_data
        )

        self.vehicle_local_position_subscriber_ = self.create_subscription(
            VehicleLocalPosition,
            f'{topic_prefix_fmu}out/vehicle_local_position',
            self.vehicle_local_position_callback,
            qos_profile_sensor_data,
        )
        self.vehicle_local_position_msg_ = VehicleLocalPosition()

        self.vehicle_global_position_subscriber = self.create_subscription(
            VehicleGlobalPosition,
            f'{topic_prefix_fmu}out/vehicle_global_position',
            self.vehicle_global_position_callback,
            qos_profile_sensor_data,
        )
        self.vehicle_global_position_msg_ = VehicleGlobalPosition()

        self.timer_ocm_ = self.create_timer(CONTROL_LOOP_PERIOD_S, self.timer_ocm_callback)
        self.display_info = self.create_timer(
            CONTROL_LOOP_PERIOD_S, self.timer_display_info_callback
        )
        self.info_count = 0
        self.setpoint = [0.0, 0.0, 0.0]

        self.get_logger().info(
            f'[dc] Controller ready: topic_prefix={topic_prefix_fmu}, loop={CONTROL_LOOP_PERIOD_S}s'
        )


def main(args=None):
    rclpy.init(args=args)
    drone_controller = DroneController()
    rclpy.spin(drone_controller)
    drone_controller.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
