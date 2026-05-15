"""Tests for generate_compose.py config loading and YAML validation."""

import os
import tempfile
import unittest

import yaml

EXAMPLE_YAML = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'realgazebo', 'yaml', 'example.yaml'
)

VALID_VEHICLE_TYPES = ['x500', 'x500_lidar_2d', 'lc_62', 'rover_ackermann', 'boat', 'rock']
VALID_FIRMWARES = ['px4', 'ardupilot', 'jsbsim']


class TestGenerateCompose(unittest.TestCase):
    """Test that generate_compose.py can load and validate YAML configs."""

    def setUp(self):
        from generate_compose import load_config, parse_spawnpoint

        self.load_config = load_config
        self.parse_spawnpoint = parse_spawnpoint

    def _make_config(self, vehicles: dict) -> str:
        for v in vehicles.values():
            if 'spawnpoint' in v and isinstance(v['spawnpoint'], (list, tuple)):
                v['spawnpoint'] = f'({", ".join(map(str, v["spawnpoint"]))})'
        config = {'build_targets': {0: '/some/path'}, 'vehicles': vehicles}
        path = os.path.join(tempfile.mkdtemp(), 'config.yaml')
        with open(path, 'w') as f:
            yaml.dump(config, f)
        return path

    def test_example_config_format(self):
        if not os.path.exists(EXAMPLE_YAML):
            self.skipTest('example.yaml not found')
        config = self.load_config(EXAMPLE_YAML)
        self.assertIn('vehicles', config)
        self.assertIn('build_targets', config)

    def test_valid_vehicle_types(self):
        vehicles = {}
        for i, vt in enumerate(VALID_VEHICLE_TYPES):
            if vt == 'rock':
                continue
            vehicles[i] = {'type': vt, 'build_target': 0, 'spawnpoint': (0, 0, 0, 0)}
        path = self._make_config(vehicles)
        config = self.load_config(path)
        self.assertEqual(len(config['vehicles']), len(vehicles))

    def test_ardupilot_firmware(self):
        vehicles = {
            0: {
                'type': 'x500',
                'firmware': 'ardupilot',
                'build_target': 0,
                'spawnpoint': (0, 0, 0, 0),
            },
        }
        path = self._make_config(vehicles)
        config = self.load_config(path)
        self.assertEqual(config['vehicles'][0]['firmware'], 'ardupilot')

    def test_jsbsim_firmware(self):
        vehicles = {
            0: {
                'type': 'x500',
                'firmware': 'jsbsim',
                'build_target': 0,
                'spawnpoint': (0, 0, 0, 0),
            },
        }
        path = self._make_config(vehicles)
        config = self.load_config(path)
        self.assertEqual(config['vehicles'][0]['firmware'], 'jsbsim')

    def test_invalid_vehicle_type_raises(self):
        vehicles = {0: {'type': 'spaceship', 'build_target': 0}}
        path = self._make_config(vehicles)
        with self.assertRaises(Exception) as ctx:
            self.load_config(path)
        self.assertIn('spaceship', str(ctx.exception))

    def test_invalid_firmware_raises(self):
        vehicles = {0: {'type': 'x500', 'firmware': 'crazyflie', 'build_target': 0}}
        path = self._make_config(vehicles)
        with self.assertRaises(Exception) as ctx:
            self.load_config(path)
        self.assertIn('crazyflie', str(ctx.exception))

    def test_parse_spawnpoint_string(self):
        result = self.parse_spawnpoint('(18.846, 14.751, -1.3, -3.14)')
        self.assertEqual(len(result), 4)
        self.assertAlmostEqual(result[0], 18.846)
        self.assertAlmostEqual(result[3], -3.14)

    def test_parse_spawnpoint_list(self):
        result = self.parse_spawnpoint([10, 20, 30, 1.57])
        self.assertEqual(result, [10, 20, 30, 1.57])

    def test_multiple_vehicles(self):
        vehicles = {
            0: {'type': 'x500', 'build_target': 0, 'spawnpoint': (0, 0, 0, 0)},
            1: {'type': 'rover_ackermann', 'build_target': 0, 'spawnpoint': (10, 10, 0, 0)},
            2: {'type': 'boat', 'build_target': 0, 'spawnpoint': (20, 20, 0, 1.57)},
        }
        path = self._make_config(vehicles)
        config = self.load_config(path)
        self.assertEqual(len(config['vehicles']), 3)

    def test_rock_type_obstacle(self):
        vehicles = {0: {'type': 'rock', 'build_target': 0, 'spawnpoint': (0, 0, 0, 0)}}
        path = self._make_config(vehicles)
        config = self.load_config(path)
        self.assertEqual(config['vehicles'][0]['type'], 'rock')

    def test_build_targets_key(self):
        config_dict = {
            'build_targets': {0: '/some/path'},
            'vehicles': {0: {'type': 'x500', 'build_target': 0, 'spawnpoint': '(0, 0, 0, 0)'}},
        }
        path = os.path.join(tempfile.mkdtemp(), 'config.yaml')
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        config = self.load_config(path)
        self.assertIn('build_targets', config)
        self.assertNotIn('px4_target', config)

    def test_empty_config_raises(self):
        path = os.path.join(tempfile.mkdtemp(), 'empty.yaml')
        with open(path, 'w') as f:
            f.write('')
        with self.assertRaises(Exception) as ctx:
            self.load_config(path)
        self.assertIn('Empty', str(ctx.exception))

    def test_missing_type_raises(self):
        vehicles = {0: {'build_target': 0, 'spawnpoint': (0, 0, 0, 0)}}
        path = self._make_config(vehicles)
        with self.assertRaises(Exception) as ctx:
            self.load_config(path)
        self.assertIn('type', str(ctx.exception))

    def test_non_dict_vehicle_raises(self):
        vehicles = {0: 'not_a_dict'}
        path = self._make_config(vehicles)
        with self.assertRaises(Exception) as ctx:
            self.load_config(path)
        self.assertIn('mapping', str(ctx.exception))

    def test_deprecated_px4_target_emits_warning(self):
        import warnings

        vehicles = {0: {'type': 'x500', 'build_target': 0, 'spawnpoint': '(0, 0, 0, 0)'}}
        config_dict = {'px4_target': {0: '/some/path'}, 'vehicles': vehicles}
        path = os.path.join(tempfile.mkdtemp(), 'deprecated.yaml')
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            config = self.load_config(path)
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            self.assertGreaterEqual(len(deprecation_warnings), 1)
            self.assertIn('px4_target', str(deprecation_warnings[0].message))
        self.assertIn('build_targets', config)
        self.assertNotIn('px4_target', config)


class TestGenerateComposeCLI(unittest.TestCase):
    """Test generate_compose.py CLI argument parsing."""

    def test_defaults(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml'])
        self.assertEqual(args.config_file, 'config.yaml')
        self.assertIsNone(args.output_file)
        self.assertEqual(args.image, 'realgazebo:base')
        self.assertEqual(args.world, 'c-track')
        self.assertEqual(args.unreal_ip, 'host.docker.internal')
        self.assertEqual(args.unreal_port, '5005')
        self.assertFalse(args.gui)
        self.assertFalse(args.validate)

    def test_validate_flag(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--validate'])
        self.assertTrue(args.validate)
        self.assertEqual(args.config_file, 'config.yaml')

    def test_image_and_world_override(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--image', 'myimage:v2', '--world', 'urban'])
        self.assertEqual(args.image, 'myimage:v2')
        self.assertEqual(args.world, 'urban')

    def test_gui_sets_headless_false(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--gui'])
        self.assertTrue(args.gui)

    def test_output_file_positional(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '/tmp/my-override.yml'])
        self.assertEqual(args.output_file, '/tmp/my-override.yml')

    def test_validate_on_example_yaml(self):
        from generate_compose import load_config

        config = load_config(EXAMPLE_YAML)
        self.assertIn('vehicles', config)
        self.assertEqual(len(config['vehicles']), 10)

    def test_validate_invalid_path_raises(self):
        from generate_compose import load_config

        with self.assertRaises(FileNotFoundError):
            load_config('/tmp/nonexistent_config.yaml')

    def test_validate_empty_config_raises(self):
        from generate_compose import load_config

        path = os.path.join(tempfile.mkdtemp(), 'empty.yaml')
        with open(path, 'w') as f:
            f.write('')
        with self.assertRaises(Exception) as ctx:
            load_config(path)
        self.assertIn('Empty', str(ctx.exception))
