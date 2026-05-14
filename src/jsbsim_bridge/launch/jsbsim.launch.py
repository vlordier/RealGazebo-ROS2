"""Launch JSBSim bridge with Gazebo visual bridge."""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    instance_id = LaunchConfiguration('instance_id').perform(context)
    aircraft = LaunchConfiguration('aircraft').perform(context)
    update_rate = LaunchConfiguration('update_rate').perform(context)
    frame_id = LaunchConfiguration('frame_id').perform(context)
    gazebo_bridge = LaunchConfiguration('gazebo_bridge').perform(context).lower() == 'true'

    ns = f'jsbsim_{instance_id}' if instance_id != '0' else 'jsbsim'

    nodes = [
        Node(
            package='jsbsim_bridge',
            executable='jsbsim_node',
            name=f'jsbsim_{instance_id}',
            namespace=ns,
            parameters=[{
                'instance_id': int(instance_id),
                'aircraft': aircraft,
                'update_rate': int(update_rate),
                'frame_id': frame_id,
            }],
            output='screen',
        ),
    ]

    if gazebo_bridge:
        # Bridge JSBSim pose to Gazebo so it appears visually
        nodes.append(Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name=f'jsbsim_gz_bridge_{instance_id}',
            arguments=[
                f'/{ns}/pose@geometry_msgs/msg/PoseStamped[gz.msgs.Pose',
                f'/{ns}/pose_ground_truth@geometry_msgs/msg/PoseStamped[gz.msgs.Pose',
            ],
            output='screen',
        ))

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('instance_id', default_value='0'),
        DeclareLaunchArgument('aircraft', default_value='c172p'),
        DeclareLaunchArgument('update_rate', default_value='250'),
        DeclareLaunchArgument('frame_id', default_value='map'),
        DeclareLaunchArgument('gazebo_bridge', default_value='true'),
        OpaqueFunction(function=launch_setup),
    ])
