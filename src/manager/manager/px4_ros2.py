from enum import Enum

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleGlobalPosition,
    VehicleLocalPosition,
    VehicleStatus,
)

# ── Constants ────────────────────────────────────────────────────────────────

CONTROL_LOOP_PERIOD_S = 0.1
QOS_DEPTH_DEFAULT = 10
PX4_CUSTOM_MAIN_MODE_OFFBOARD = 6.0
DEFAULT_TAKEOFF_ALTITUDE_M = 20.0
MOVE_DISTANCE_DEFAULT_M = 300.0
MOVE_DISTANCE_EAST_M = 100.0
MOVE_DISTANCE_FALLBACK_M = 70.0
ARM_CONFIRM = 1.0
DISARM_PARAM = 0.0


class Vehicle(Enum):
    DRONE = 0
    ROVER = 1
    BOAT = 2
    UNKNOWN = 99


# Vehicle-specific move distances: some vehicles need smaller offset
VEHICLE_MOVE_DISTANCES: dict[int, tuple[float, float]] = {
    # system_id: (y_offset, x_offset)
    9: (0.0, -MOVE_DISTANCE_EAST_M),
    10: (0.0, -MOVE_DISTANCE_EAST_M),
}

VEHICLE_MOVE_FALLBACK = (-MOVE_DISTANCE_DEFAULT_M, 0.0)


class PX4ROS2(Node):
    def __init__(self):
        super().__init__('px4_ros2')
        self.declare_parameter('system_id', 1)
        self.system_id_ = self.get_parameter('system_id').get_parameter_value().integer_value
        self.declare_parameter('vehicle_type', 'iris')
        try:
            self.vehicle_type_ = Vehicle[
                self.get_parameter('vehicle_type').get_parameter_value().string_value.upper()
            ]
        except KeyError:
            self.vehicle_type_ = Vehicle.UNKNOWN

        self.get_logger().info(
            f'[px4] Initialized: system={self.system_id_} type={self.vehicle_type_.name}'
        )

        topic_prefix_fmu = f'vehicle{self.system_id_}/fmu/'
        topic_prefix_manager = f'vehicle{self.system_id_}/manager/'

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
            TrajectorySetpoint, f'{topic_prefix_fmu}in/trajectory_setpoint', QOS_DEPTH_DEFAULT
        )

        self.vehicle_command_publisher_ = self.create_publisher(
            VehicleCommand, f'{topic_prefix_fmu}in/vehicle_command', QOS_DEPTH_DEFAULT
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

        self.main_cmd_subscriber_ = self.create_subscription(
            String, f'{topic_prefix_manager}in/main_cmd', self.main_cmd_callback, QOS_DEPTH_DEFAULT
        )
        self.main_cmd_msg_ = String()

        self.timer_ocm_ = self.create_timer(CONTROL_LOOP_PERIOD_S, self.timer_ocm_callback)
        self.arrive_target_ = False

    def vehicle_local_position_callback(self, msg):
        self.vehicle_local_position_msg_ = msg

    def vehicle_global_position_callback(self, msg):
        self.vehicle_global_position_msg_ = msg

    def main_cmd_callback(self, msg):
        cmd = msg.data
        self.get_logger().info(f'[px4] Received command: {cmd}')
        match cmd:
            case 'ARM':
                self.control_arm()
            case 'DISARM':
                self.control_disarm()
            case 'OFFBOARD':
                self.control_offboard()
            case 'TAKEOFF':
                self.control_takeoff(DEFAULT_TAKEOFF_ALTITUDE_M)
            case 'START':
                self._handle_start()

    def _handle_start(self):
        offset_y, offset_x = VEHICLE_MOVE_DISTANCES.get(self.system_id_, VEHICLE_MOVE_FALLBACK)
        pos = self.vehicle_local_position_msg_
        self.control_setpoint(pos.x + offset_x, pos.y + offset_y, pos.z, pos.heading)
        self.get_logger().info(
            f'[px4] START: moving by ({offset_x:.0f}, {offset_y:.0f}) for system {self.system_id_}'
        )

    def vehicle_status_callback(self, msg):
        self.vehicle_status_msg_ = msg
        self.get_logger().debug(f'[px4] Status: nav_state={msg.nav_state} armed={msg.arming_state}')

    def timer_ocm_callback(self):
        self.ocm_publisher_.publish(self.ocm_msg_qhac_)

    def control_arm(self):
        arm_cmd = VehicleCommand()
        arm_cmd.target_system = self.system_id_
        arm_cmd.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        arm_cmd.param1 = ARM_CONFIRM
        arm_cmd.confirmation = True
        arm_cmd.from_external = True
        self.vehicle_command_publisher_.publish(arm_cmd)
        self.get_logger().info(f'[px4] ARM system {self.system_id_}')

    def control_takeoff(self, altitude):
        takeoff_cmd = VehicleCommand()
        takeoff_cmd.target_system = self.system_id_
        takeoff_cmd.command = VehicleCommand.VEHICLE_CMD_NAV_TAKEOFF
        takeoff_cmd.param1 = -1.0
        takeoff_cmd.param4 = self.vehicle_local_position_msg_.heading
        takeoff_cmd.param5 = self.vehicle_global_position_msg_.lat
        takeoff_cmd.param6 = self.vehicle_global_position_msg_.lon
        takeoff_cmd.param7 = self.vehicle_global_position_msg_.alt + altitude
        self.vehicle_command_publisher_.publish(takeoff_cmd)
        self.get_logger().info(f'[px4] TAKEOFF {altitude}m')

    def control_disarm(self):
        disarm_cmd = VehicleCommand()
        disarm_cmd.target_system = self.system_id_
        disarm_cmd.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
        disarm_cmd.param1 = DISARM_PARAM
        disarm_cmd.confirmation = True
        self.vehicle_command_publisher_.publish(disarm_cmd)
        self.get_logger().info(f'[px4] DISARM system {self.system_id_}')

    def control_offboard(self):
        offboard_cmd = VehicleCommand()
        offboard_cmd.target_system = self.system_id_
        offboard_cmd.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
        offboard_cmd.param1 = 1.0
        offboard_cmd.param2 = PX4_CUSTOM_MAIN_MODE_OFFBOARD
        offboard_cmd.from_external = True
        self.vehicle_command_publisher_.publish(offboard_cmd)
        self.get_logger().info('[px4] OFFBOARD mode')

    def control_setpoint(self, x, y, z, heading=None):
        setpoint_cmd = TrajectorySetpoint()
        setpoint_cmd.position[0] = x
        setpoint_cmd.position[1] = y
        setpoint_cmd.position[2] = z
        if heading is not None:
            setpoint_cmd.yaw = heading
        self.traj_setpoint_publisher_.publish(setpoint_cmd)
        self.get_logger().debug(f'[px4] Setpoint ({x:.1f}, {y:.1f}, {z:.1f})')


def main(args=None):
    rclpy.init(args=args)
    px4ros2 = PX4ROS2()
    try:
        rclpy.spin(px4ros2)
    except KeyboardInterrupt:
        px4ros2.get_logger().info('[px4] Shutting down')
    finally:
        px4ros2.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
