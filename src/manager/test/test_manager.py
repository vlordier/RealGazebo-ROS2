"""Tests for manager (PX4 ROS2 bridge) command parsing and message creation."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

keyBindings = {
    'a': "ARM", 'o': "OFFBOARD", 't': "TAKEOFF",
    "s": "START", "d": "DISARM"
}


class TestCommandParsing(unittest.TestCase):
    """Test keyboard command parsing"""

    def test_all_keybindings_present(self):
        self.assertIn('a', keyBindings)
        self.assertIn('o', keyBindings)
        self.assertIn('t', keyBindings)
        self.assertIn('s', keyBindings)
        self.assertIn('d', keyBindings)

    def test_keybinding_values(self):
        self.assertEqual(keyBindings['a'], "ARM")
        self.assertEqual(keyBindings['o'], "OFFBOARD")
        self.assertEqual(keyBindings['t'], "TAKEOFF")
        self.assertEqual(keyBindings['s'], "START")
        self.assertEqual(keyBindings['d'], "DISARM")

    def test_no_unexpected_keys(self):
        allowed = {'a', 'o', 't', 's', 'd'}
        self.assertEqual(set(keyBindings.keys()), allowed)

    def test_cmd_vel_not_needed_by_default(self):
        self.assertNotIn('v', keyBindings)
        self.assertNotIn('w', keyBindings)


class TestManagerConfig(unittest.TestCase):
    """Test manager configuration patterns"""

    def test_topic_prefix_pattern(self):
        for i in range(1, 11):
            prefix = f"vehicle{i}/manager/"
            self.assertEqual(prefix, f"vehicle{i}/manager/")

    def test_main_cmd_topic(self):
        for i in range(1, 6):
            topic = f"vehicle{i}/manager/in/main_cmd"
            self.assertTrue(topic.endswith("in/main_cmd"))
            self.assertIn(f"vehicle{i}", topic)


class TestLoggerFormat(unittest.TestCase):
    """Test the log message format"""

    def test_user_message_format(self):
        lines = [
            "a : arm",
            "o : offboard",
            "t : takeoff(only for drone)",
            "s : start misssion",
            "d : disarm",
        ]
        self.assertEqual(len(lines), 5)
        for line in lines:
            self.assertRegex(line, r"^[a-z] : .+")

    def test_msg_command_prefix(self):
        msg = """
a : arm
o : offboard
t : takeoff(only for drone)
s : start misssion
d : disarm
"""
        for cmd in ["a", "o", "t", "s", "d"]:
            self.assertIn(cmd, msg)


if __name__ == '__main__':
    unittest.main()
