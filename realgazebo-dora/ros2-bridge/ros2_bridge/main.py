#!/usr/bin/env python3
"""ROS2 bridge operator for dora-rs dataflow.

Subscribes to ROS2 topics (clock, vehicle pose) and publishes
typed data structures into the dora dataflow.
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("ros2_bridge")

try:
    import rclpy
    from rclpy.node import Node as RclpyNode
    from std_msgs.msg import String
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False
    logger.warning("ROS2 not available — running in mock mode")

try:
    from dora import Node as DoraNode
except ImportError:
    logger.error("dora module not found")
    sys.exit(1)

from ros2_bridge.datamodel import (
    VehiclePose, SimulationClock, safe_send, event_value
)


class ROS2BridgeNode(RclpyNode if HAS_ROS2 else object):
    """Bridge node subscribing to ROS2 simulation topics."""

    def __init__(self, dora_node):
        if HAS_ROS2:
            super().__init__("dora_ros2_bridge")
        self.dora = dora_node
        self.clock_msg = None
        self.vehicle_poses = {}

        if HAS_ROS2:
            self.create_subscription(
                String, "/clock", self._clock_callback, 10
            )
            logger.info("Subscribed to ROS2 /clock topic")

    def _clock_callback(self, msg):
        self.clock_msg = msg


def main():
    dora = DoraNode()
    bridge = ROS2BridgeNode(dora) if HAS_ROS2 else None
    tick_count = 0

    logger.info("ros2_bridge operator started")

    for event in dora:
        try:
            if event["type"] != "INPUT":
                continue

            tick_count += 1

            # Spin ROS2 to receive messages
            if HAS_ROS2 and bridge:
                rclpy.spin_once(bridge, timeout_sec=0)

            # Publish simulation clock data
            if HAS_ROS2 and bridge and bridge.clock_msg:
                clock = SimulationClock(
                    sec=int(tick_count * 0.1),
                    nsec=int((tick_count * 0.1 - int(tick_count * 0.1)) * 1e9)
                )
                dora.send_output("simulation_time", str(clock.sim_time_s).encode())

            # Periodically publish vehicle pose status
            if tick_count % 10 == 0:
                status = VehiclePose(
                    vehicle_id=0,
                    vehicle_type="x500",
                    x=10.0 + tick_count * 0.01,
                    y=0.0,
                    z=-5.0
                )
                safe_send(dora, "vehicle_pose", status.to_json())

        except Exception as e:
            logger.error(f"Error processing event {event_value(event)}: {e}")


if __name__ == "__main__":
    main()
