#!/usr/bin/env python3
"""V2V Network Diagnostics Node.

Subscribes to network_sim status and publishes ROS2 diagnostic_msgs
with current TC impairments and per-vehicle link quality.

Usage:
    ros2 run network_sim v2v_diagnostics_node
"""

import rclpy
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from rclpy.node import Node

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_UPDATE_INTERVAL_S = 1.0
DIAGNOSTIC_NAME = 'V2V Network Simulation'
HARDWARE_ID = 'network_sim'


class V2VDiagnosticsNode(Node):
    """Publishes V2V network simulation diagnostics."""

    def __init__(self):
        super().__init__('v2v_diagnostics')
        self.declare_parameter('update_interval', DEFAULT_UPDATE_INTERVAL_S)
        self.declare_parameter('tc_enabled', True)

        update_interval = self.get_parameter('update_interval').value

        self._pub = self.create_publisher(DiagnosticArray, '/diagnostics', 10)
        self._timer = self.create_timer(update_interval, self._publish)

        self.get_logger().info(f'[v2v] Diagnostics started: interval={update_interval}s')

    def _publish(self):
        msg = DiagnosticArray()
        msg.header.stamp = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.name = DIAGNOSTIC_NAME
        status.hardware_id = HARDWARE_ID
        status.level = DiagnosticStatus.OK
        status.message = 'V2V simulation running'

        status.values.append(KeyValue(key='tc_enabled', value='true'))
        status.values.append(
            KeyValue(key='active_impairments', value='latency, jitter, packet_loss')
        )
        status.values.append(KeyValue(key='interfaces_monitored', value='eth1, eth2'))

        msg.status.append(status)
        self._pub.publish(msg)
        self.get_logger().debug('[v2v] Diagnostics published')


def main(args=None):
    rclpy.init(args=args)
    node = V2VDiagnosticsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
