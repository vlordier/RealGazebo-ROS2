"""Tests for generate_compose.py config loading, validation, and CLI parsing."""

import os
import tempfile
import warnings

import pytest
import yaml


def _make_config(vehicles):
    for v in vehicles.values():
        if 'spawnpoint' in v and isinstance(v['spawnpoint'], (list, tuple)):
            v['spawnpoint'] = f'({", ".join(map(str, v["spawnpoint"]))})'
    config = {'build_targets': {0: '/some/path'}, 'vehicles': vehicles}
    path = os.path.join(tempfile.mkdtemp(), 'config.yaml')
    with open(path, 'w') as f:
        yaml.dump(config, f)
    return path


class TestConfigLoading:
    """Tests for YAML config loading and validation."""

    def test_example_config_format(self, example_config):
        assert 'vehicles' in example_config
        assert 'build_targets' in example_config

    def test_valid_vehicle_types(self):
        from generate_compose import load_config

        vehicles = {
            i: {'type': t, 'build_target': 0, 'spawnpoint': (0, 0, 0, 0)}
            for i, t in enumerate(['x500', 'x500_lidar_2d', 'lc_62', 'rover_ackermann', 'boat'])
        }
        config = load_config(_make_config(vehicles))
        assert len(config['vehicles']) == 5

    def test_ardupilot_firmware(self):
        from generate_compose import load_config

        config = load_config(
            _make_config(
                {
                    0: {
                        'type': 'x500',
                        'firmware': 'ardupilot',
                        'build_target': 0,
                        'spawnpoint': (0, 0, 0, 0),
                    }
                }
            )
        )
        assert config['vehicles'][0]['firmware'] == 'ardupilot'

    def test_jsbsim_firmware(self):
        from generate_compose import load_config

        config = load_config(
            _make_config(
                {
                    0: {
                        'type': 'x500',
                        'firmware': 'jsbsim',
                        'build_target': 0,
                        'spawnpoint': (0, 0, 0, 0),
                    }
                }
            )
        )
        assert config['vehicles'][0]['firmware'] == 'jsbsim'

    def test_invalid_vehicle_type_raises(self):
        from generate_compose import load_config

        with pytest.raises(Exception, match='spaceship'):
            load_config(_make_config({0: {'type': 'spaceship', 'build_target': 0}}))

    def test_invalid_firmware_raises(self):
        from generate_compose import load_config

        with pytest.raises(Exception, match='crazyflie'):
            load_config(
                _make_config({0: {'type': 'x500', 'firmware': 'crazyflie', 'build_target': 0}})
            )

    def test_empty_config_raises(self):
        from generate_compose import load_config

        path = os.path.join(tempfile.mkdtemp(), 'empty.yaml')
        with open(path, 'w') as f:
            f.write('')
        with pytest.raises(Exception, match='Empty'):
            load_config(path)

    def test_missing_type_raises(self):
        from generate_compose import load_config

        with pytest.raises(Exception, match='type'):
            load_config(_make_config({0: {'build_target': 0, 'spawnpoint': (0, 0, 0, 0)}}))

    def test_non_dict_vehicle_raises(self):
        from generate_compose import load_config

        with pytest.raises(Exception, match='mapping'):
            load_config(_make_config({0: 'not_a_dict'}))

    def test_deprecated_px4_target_emits_warning(self):
        from generate_compose import load_config

        vehicles = {0: {'type': 'x500', 'build_target': 0, 'spawnpoint': '(0, 0, 0, 0)'}}
        config_dict = {'px4_target': {0: '/some/path'}, 'vehicles': vehicles}
        path = os.path.join(tempfile.mkdtemp(), 'deprecated.yaml')
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            config = load_config(path)
            dw = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(dw) >= 1
            assert 'px4_target' in str(dw[0].message)
        assert 'build_targets' in config
        assert 'px4_target' not in config


class TestSpawnpointParsing:
    """Tests for spawnpoint string parsing."""

    def test_parse_string_tuple(self):
        from generate_compose import parse_spawnpoint

        result = parse_spawnpoint('(18.846, 14.751, -1.3, -3.14)')
        assert len(result) == 4
        assert abs(result[0] - 18.846) < 1e-6
        assert abs(result[3] - (-3.14)) < 1e-6

    def test_parse_list(self):
        from generate_compose import parse_spawnpoint

        result = parse_spawnpoint([10, 20, 30, 1.57])
        assert result == [10, 20, 30, 1.57]

    def test_parse_invalid_raises(self):
        from generate_compose import parse_spawnpoint

        with pytest.raises(ValueError, match='Invalid spawnpoint'):
            parse_spawnpoint('not-a-tuple')


class TestGenerateComposeCLI:
    """Tests for CLI argument parsing."""

    def test_defaults(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml'])
        assert args.config_file == 'config.yaml'
        assert args.output_file is None
        assert args.image == 'realgazebo:full'
        assert args.world == 'c-track'
        assert args.unreal_ip == 'host.docker.internal'
        assert args.unreal_port == '5005'
        assert not args.gui
        assert not args.validate

    def test_validate_flag(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--validate'])
        assert args.validate
        assert args.config_file == 'config.yaml'

    def test_image_and_world_override(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--image', 'myimage:v2', '--world', 'urban'])
        assert args.image == 'myimage:v2'
        assert args.world == 'urban'

    def test_gui_flag(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '--gui'])
        assert args.gui

    def test_output_file_positional(self):
        from generate_compose import parse_args

        args = parse_args(['config.yaml', '/tmp/my-override.yml'])
        assert args.output_file == '/tmp/my-override.yml'

    def test_validate_on_example_yaml(self, example_config):
        assert 'vehicles' in example_config
        assert len(example_config['vehicles']) == 10

    def test_validate_invalid_path_raises(self):
        from generate_compose import load_config

        with pytest.raises(FileNotFoundError):
            load_config('/tmp/nonexistent_config.yaml')

    def test_validate_empty_config_raises(self):
        from generate_compose import load_config

        path = os.path.join(tempfile.mkdtemp(), 'empty.yaml')
        with open(path, 'w') as f:
            f.write('')
        with pytest.raises(Exception, match='Empty'):
            load_config(path)
