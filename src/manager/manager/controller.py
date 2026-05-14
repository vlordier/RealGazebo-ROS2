import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String

from manager.constants import KEY_BINDINGS, MAIN_CMD_TOPIC_TEMPLATE, USAGE_MESSAGE


def parse_vehicle_count(node: Node) -> int:
    node.declare_parameter('vehicles', 0)
    return node.get_parameter('vehicles').get_parameter_value().integer_value


def parse_cmd_vel_flag(node: Node) -> bool:
    node.declare_parameter('cmd_vel_needed', False)
    return node.get_parameter('cmd_vel_needed').get_parameter_value().bool_value


def main(args=None):
    rclpy.init()
    node = rclpy.create_node('px4_ros2_controller')

    vehicles = parse_vehicle_count(node)
    cmd_vel_needed = parse_cmd_vel_flag(node)
    main_cmd_publishers = []

    if cmd_vel_needed:
        cmd_vel_publisher = node.create_publisher(Twist, 'cmd_vel', 10)

    for i in range(1, vehicles + 1):
        topic = MAIN_CMD_TOPIC_TEMPLATE.format(i=i)
        main_cmd_publishers.append(node.create_publisher(String, topic, 10))

    node.get_logger().info(
        f'[ctrl] Controller ready: {vehicles} vehicle(s), '
        f'cmd_vel={"yes" if cmd_vel_needed else "no"}'
    )

    try:
        print(USAGE_MESSAGE)
        while True:
            key = _read_key()
            if not key:
                continue
            if key in KEY_BINDINGS:
                cmd = KEY_BINDINGS[key]
                node.get_logger().info(f"[ctrl] Key '{key}' -> {cmd}")
                if cmd_vel_needed and key == 's':
                    twist = Twist()
                    twist.linear.x = 1.0
                    cmd_vel_publisher.publish(twist)
                msg = String()
                msg.data = cmd
                for pub in main_cmd_publishers:
                    pub.publish(msg)
            elif key == '\x03':
                node.get_logger().info('[ctrl] Ctrl+C, shutting down')
                break
    except Exception as e:
        node.get_logger().error(f'[ctrl] Error: {e}')


def _read_key() -> str | None:
    """Read a single keypress from stdin, or None if no key available."""
    import select as _select
    import sys as _sys
    import termios as _termios
    import tty as _tty

    settings = _termios.tcgetattr(_sys.stdin)
    try:
        _tty.setcbreak(_sys.stdin.fileno())
        if _select.select([_sys.stdin], [], [], 0)[0]:
            return _sys.stdin.read(1)
        return None
    finally:
        _termios.tcsetattr(_sys.stdin, _termios.TCSADRAIN, settings)


if __name__ == '__main__':
    main()
