import time

import rclpy
from launch import LaunchDescription
from launch.actions import (
    OpaqueFunction,
)
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    uv_process_list = []
    rclpy.init()
    node = rclpy.create_node('topic_getter')
    time.sleep(5)
    topics = node.get_topic_names_and_types()
    vehicles = 0
    cmd_vel_needed = False
    if topics:
        for topic_name, _topic_type in topics:
            if '/fmu/out/timesync_status' in topic_name:
                vehicles += 1

            if '/cmd_vel' in topic_name:
                cmd_vel_needed = True

    node.destroy_node()
    rclpy.shutdown()
    for i in range(vehicles):
        px4_ros2_node = Node(
            package='manager',
            executable='px4_ros2',
            parameters=[{'system_id': i + 1, 'use_sim_time': True}],
        )
        uv_process_list.append(px4_ros2_node)

    controller_node = Node(
        package='manager',
        executable='controller',
        parameters=[{'vehicles': vehicles, 'cmd_vel_needed': cmd_vel_needed, 'use_sim_time': True}],
        prefix='xterm -e',
    )

    nodes_to_start = [
        *uv_process_list,
        controller_node,
    ]

    return nodes_to_start


def generate_launch_description():
    declared_arguments = []

    return LaunchDescription([*declared_arguments, OpaqueFunction(function=launch_setup)])
