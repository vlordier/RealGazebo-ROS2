"""Shared constants for the manager package.

These are safe to import without ROS2 dependencies.
"""

KEY_BINDINGS = {
    'a': 'ARM',
    'o': 'OFFBOARD',
    't': 'TAKEOFF',
    's': 'START',
    'd': 'DISARM',
}

USAGE_MESSAGE = """
  a : arm
  o : offboard
  t : takeoff (drone only)
  s : start mission
  d : disarm
"""

MAIN_CMD_TOPIC_TEMPLATE = 'vehicle{i}/manager/in/main_cmd'
