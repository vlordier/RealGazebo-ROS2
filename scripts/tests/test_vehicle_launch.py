"""Validate vehicle.launch.py startup logic, constants, and launch config."""

import ast
import os
import re

LAUNCH_FILE = os.path.join(
    os.path.dirname(__file__),
    '..',
    '..',
    'src',
    'realgazebo',
    'launch',
    'vehicle.launch.py',
)


class TestVehicleLaunchConfig:
    """AST-level validation of vehicle.launch.py structure and conventions."""

    def test_timing_constants_defined(self):
        with open(LAUNCH_FILE) as f:
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
        assert 'VEHICLE_SPAWN_DELAY_S' in constants
        assert 'VEHICLE_ACTION_INTERVAL_S' in constants
        assert constants['VEHICLE_SPAWN_DELAY_S'] >= 0
        assert constants['VEHICLE_ACTION_INTERVAL_S'] >= 0

    def test_launch_arguments_have_defaults_or_required(self):
        with open(LAUNCH_FILE) as f:
            content = f.read()
        args_with_default = set(
            re.findall(r"DeclareLaunchArgument\(\s*'(\w+)'[^)]*default_value\s*=", content)
        )
        all_args = set(re.findall(r"DeclareLaunchArgument\(\s*'(\w+)'", content))
        args_without_default = all_args - args_with_default
        assert 'instance_id' in args_without_default, 'instance_id should be required'
        assert 'firmware' in args_without_default, 'firmware should be required'
        assert 'skip_params' in args_with_default, 'skip_params should have a default'

    def test_firmware_default_removed(self):
        with open(LAUNCH_FILE) as f:
            content = f.read()
        firmware_defaults = re.findall(
            r"DeclareLaunchArgument\(\s*'firmware'[^)]*default_value\s*=", content
        )
        assert len(firmware_defaults) == 0, 'firmware should have no default in vehicle.launch.py'
