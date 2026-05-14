"""Tests for manager (PX4 ROS2 bridge) command parsing and message creation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from manager.constants import KEY_BINDINGS, MAIN_CMD_TOPIC_TEMPLATE, USAGE_MESSAGE


class TestKeyBindings(unittest.TestCase):
    """Test keyboard command mapping from controller module."""

    def test_all_keys_present(self):
        self.assertIn('a', KEY_BINDINGS)
        self.assertIn('o', KEY_BINDINGS)
        self.assertIn('t', KEY_BINDINGS)
        self.assertIn('s', KEY_BINDINGS)
        self.assertIn('d', KEY_BINDINGS)

    def test_values(self):
        self.assertEqual(KEY_BINDINGS['a'], 'ARM')
        self.assertEqual(KEY_BINDINGS['o'], 'OFFBOARD')
        self.assertEqual(KEY_BINDINGS['t'], 'TAKEOFF')
        self.assertEqual(KEY_BINDINGS['s'], 'START')
        self.assertEqual(KEY_BINDINGS['d'], 'DISARM')

    def test_exact_count(self):
        self.assertEqual(len(KEY_BINDINGS), 5)

    def test_keys_are_expected(self):
        self.assertEqual(set(KEY_BINDINGS.keys()), {'a', 'o', 't', 's', 'd'})


class TestTopicTemplate(unittest.TestCase):
    """Test the main_cmd topic template."""

    def test_topic_format(self):
        for i in [1, 3, 10]:
            topic = MAIN_CMD_TOPIC_TEMPLATE.format(i=i)
            self.assertTrue(topic.startswith('vehicle'))
            self.assertTrue(topic.endswith('in/main_cmd'))
            self.assertEqual(topic, f'vehicle{i}/manager/in/main_cmd')


class TestUsageMessage(unittest.TestCase):
    """Test the usage message includes all commands."""

    def test_all_commands_in_message(self):
        for cmd in ['a', 'o', 't', 's', 'd']:
            self.assertIn(cmd, USAGE_MESSAGE)

    def test_contains_arm(self):
        self.assertIn('arm', USAGE_MESSAGE.lower())

    def test_contains_disarm(self):
        self.assertIn('disarm', USAGE_MESSAGE.lower())


if __name__ == '__main__':
    unittest.main()
