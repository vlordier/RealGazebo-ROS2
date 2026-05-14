"""Launch ArduPilot SITL with MAVROS ROS2 bridge.

Starts MAVROS to bridge ArduPilot MAVLink (UDP) to ROS2 topics.
Vehicle state (pose, velocity, battery, status) becomes available
as standard ROS2 messages for dora dataflow and UE5 visualization.

Usage:
    ros2 launch ardupilot_bridge ardupilot_bridge.launch.py \
        instance_id:=0 fcu_url:=udp://127.0.0.1:14550@14555
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import OpaqueFunction
from ament_index_python.packages import get_package_share_directory
import os


def launch_setup(context, *args, **kwargs):
    instance_id = LaunchConfiguration('instance_id').perform(context)
    fcu_url = LaunchConfiguration('fcu_url').perform(context)
    tgt_system = LaunchConfiguration('tgt_system').perform(context)
    gcs_url = LaunchConfiguration('gcs_url').perform(context)

    ns = f'vehicle{int(instance_id) + 1}'

    # MAVROS node: bridges ArduPilot MAVLink → ROS2
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        namespace=ns,
        parameters=[{
            'fcu_url': fcu_url,
            'gcs_url': gcs_url,
            'tgt_system': int(tgt_system),
            'tgt_component': 1,
            'fcu_protocol': 'v2.0',
        }],
        output='screen',
    )

    # Bridge MAVROS pose to Gazebo visual
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name=f'mavros_gz_bridge_{instance_id}',
        arguments=[
            f'/{ns}/mavros/local_position/pose]geometry_msgs/msg/PoseStamped@gz.msgs.Pose',
        ],
        output='screen',
    )

    return [mavros_node, gz_bridge]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('instance_id', default_value='0'),
        DeclareLaunchArgument('fcu_url',
            default_value='udp://127.0.0.1:14550@14555'),
        DeclareLaunchArgument('tgt_system', default_value='1'),
        DeclareLaunchArgument('gcs_url', default_value=''),
        OpaqueFunction(function=launch_setup),
    ])
