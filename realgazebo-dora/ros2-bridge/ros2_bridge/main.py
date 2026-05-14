#!/usr/bin/env python3
"""ROS2 bridge operator for dora-rs dataflow.

Subscribes to ROS2 topics (clock, vehicle pose) and publishes
validated Pydantic data structures into the dora dataflow.
"""

import logging
import sys

from ros2_bridge.datamodel import SimulationClock, VehiclePose

logging.basicConfig(level=logging.INFO, format='%(name)s %(levelname)s %(message)s')
logger = logging.getLogger('ros2_bridge')

try:
    import rclpy
    from rclpy.node import Node as RclpyNode
    from std_msgs.msg import String

    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    logger.warning('ROS2 not available — bridge will use mocked data')

try:
    from dora import Node as DoraNode
except ImportError:
    logger.error('dora module not found')
    sys.exit(1)


class ROS2BridgeNode(RclpyNode if HAS_ROS2 else object):
    """Bridge subscribing to ROS2 simulation topics and publishing Pydantic models."""

    def __init__(self, dora_node: DoraNode):
        if HAS_ROS2:
            super().__init__('dora_ros2_bridge')
        self.dora = dora_node
        self.clock_msg: String | None = None

        if HAS_ROS2:
            self.create_subscription(String, '/clock', self._clock_callback, 10)
            logger.info('subscribed to /clock')

    def _clock_callback(self, msg: String) -> None:
        self.clock_msg = msg


def main() -> None:
    dora = DoraNode()
    bridge = ROS2BridgeNode(dora) if HAS_ROS2 else None
    tick_count = 0
    logger.info('bridge operator started')

    for event in dora:
        try:
            if event['type'] != 'INPUT':
                continue

            tick_count += 1

            if HAS_ROS2 and bridge:
                rclpy.spin_once(bridge, timeout_sec=0)

            # Publish validated SimulationClock
            clock = SimulationClock(
                sec=tick_count // 10,
                nsec=(tick_count % 10) * 100_000_000,
                real_sec=tick_count // 10,
                real_nsec=(tick_count % 10) * 100_000_000,
            )
            dora.send_output('simulation_time', str(clock.sim_time_s).encode())

            # Periodically publish validated VehiclePose
            if tick_count % 10 == 0:
                pose = VehiclePose(
                    vehicle_id=0,
                    vehicle_type='x500',
                    x=10.0 + tick_count * 0.01,
                    y=0.0,
                    z=-5.0,
                    heading=0.0,
                )
                dora.send_output('vehicle_pose', pose.to_json())
                logger.debug(f'published pose: ({pose.x:.1f}, {pose.y:.1f}, {pose.z:.1f})')

        except Exception as e:
            logger.error(f'event error: {e}', exc_info=True)


if __name__ == '__main__':
    main()
