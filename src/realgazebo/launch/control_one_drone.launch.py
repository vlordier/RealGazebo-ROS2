from launch import LaunchDescription
from launch.actions import (
    OpaqueFunction,
)
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    controller_node = Node(
        package='drone_controller',
        executable='drone_controller',
        parameters=[{'use_sim_time': True}],
    )

    nodes_to_start = [
        controller_node,
    ]

    return nodes_to_start


def generate_launch_description():
    declared_arguments = []

    return LaunchDescription([*declared_arguments, OpaqueFunction(function=launch_setup)])
