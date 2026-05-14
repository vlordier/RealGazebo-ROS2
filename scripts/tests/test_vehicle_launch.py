"""Validate vehicle.launch.py startup logic, constants, and launch config."""

import os
import re
import unittest


class TestVehicleLaunchConfig(unittest.TestCase):
    """Test launch config and timing constants from vehicle.launch.py."""

    def test_timing_constants_defined(self):
        """Vehicle spawn and action interval constants are positive."""
        import ast

        launch_file = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'src',
            'realgazebo',
            'launch',
            'vehicle.launch.py',
        )
        with open(launch_file) as f:
            tree = ast.parse(f.read())

        constants = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id in ('VEHICLE_SPAWN_DELAY_S', 'VEHICLE_ACTION_INTERVAL_S')
                    ) and isinstance(node.value, ast.Constant):
                        constants[target.id] = node.value.value

        self.assertIn('VEHICLE_SPAWN_DELAY_S', constants)
        self.assertIn('VEHICLE_ACTION_INTERVAL_S', constants)
        self.assertGreaterEqual(constants['VEHICLE_SPAWN_DELAY_S'], 0)
        self.assertGreaterEqual(constants['VEHICLE_ACTION_INTERVAL_S'], 0)

    def test_launch_arguments_have_defaults_or_required(self):
        """All launch arguments are properly declared (checked via source regex)."""
        launch_file = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'src',
            'realgazebo',
            'launch',
            'vehicle.launch.py',
        )
        with open(launch_file) as f:
            content = f.read()

        # Find all DeclareLaunchArgument calls with name and default_value
        args_with_default = set(
            re.findall(r"DeclareLaunchArgument\(\s*'(\w+)'[^)]*default_value\s*=", content)
        )
        # Find all DeclareLaunchArgument names, then remove those with defaults
        all_args = set(re.findall(r"DeclareLaunchArgument\(\s*'(\w+)'", content))
        args_without_default = all_args - args_with_default

        self.assertIn(
            'instance_id', args_without_default, 'instance_id should be required (no default)'
        )
        self.assertIn(
            'firmware',
            args_without_default,
            'firmware should be required (no default after refactor)',
        )
        self.assertIn('skip_params', args_with_default, 'skip_params should have a default')

    def test_firmware_default_removed(self):
        """vehicle.launch.py should NOT have a firmware default_value
        (single source of truth is generate_compose.py).
        """
        launch_file = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'src',
            'realgazebo',
            'launch',
            'vehicle.launch.py',
        )
        with open(launch_file) as f:
            content = f.read()
        # Search for firmware with a default_value
        firmware_defaults = re.findall(
            r"DeclareLaunchArgument\(\s*'firmware'[^)]*default_value\s*=", content
        )
        self.assertEqual(
            len(firmware_defaults), 0, 'firmware should have no default_value in vehicle.launch.py'
        )


if __name__ == '__main__':
    unittest.main()
