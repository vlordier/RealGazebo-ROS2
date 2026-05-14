"""Launch file for V2V network diagnostics."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            Node(
                package='network_sim',
                executable='v2v_diagnostics.py',
                name='v2v_diagnostics',
                output='screen',
                parameters=[{'update_interval': 1.0}],
            ),
        ]
    )
