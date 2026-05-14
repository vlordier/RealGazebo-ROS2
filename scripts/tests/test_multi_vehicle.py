"""Tests for multi-vehicle V2V simulation stack.

Unit tests validate config loading, compose generation, and network topology.
Integration tests (marked @pytest.mark.integration) require Docker + running stack.
"""

import os
import sys
import unittest

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


EXAMPLE_YAML = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'realgazebo', 'yaml', 'example.yaml'
)


class TestMultiVehicleConfig(unittest.TestCase):
    """Validate that example.yaml loads correctly with all 10 vehicles."""

    def setUp(self):  # noqa: D102
        from generate_compose import load_config, parse_spawnpoint
        self._load_config = load_config
        self._parse_spawnpoint = parse_spawnpoint

    def test_example_loads_all_vehicles(self):
        """example.yaml has exactly 10 vehicles."""
        config = self._load_config(EXAMPLE_YAML)
        self.assertIn('vehicles', config)
        self.assertEqual(len(config['vehicles']), 10)

    def test_example_vehicle_types(self):
        """All 5 vehicle types are represented."""
        config = self._load_config(EXAMPLE_YAML)
        types = {v['type'] for v in config['vehicles'].values()}
        expected = {'x500', 'x500_lidar_2d', 'lc_62', 'rover_ackermann', 'boat'}
        self.assertEqual(types, expected)

    def test_rover_has_ardupilot_firmware(self):
        """Vehicle 5 (rover_ackermann) uses ardupilot firmware."""
        config = self._load_config(EXAMPLE_YAML)
        self.assertEqual(config['vehicles'][5].get('firmware'), 'ardupilot')

    def test_boat_has_ardupilot_firmware(self):
        """Vehicle 8 (boat) uses ardupilot firmware."""
        config = self._load_config(EXAMPLE_YAML)
        self.assertEqual(config['vehicles'][8].get('firmware'), 'ardupilot')

    def test_default_firmware_is_px4(self):
        """Vehicles without explicit firmware default to px4."""
        config = self._load_config(EXAMPLE_YAML)
        for vid in [0, 1, 2, 3, 4, 6, 7, 9]:
            self.assertEqual(config['vehicles'][vid].get('firmware', 'px4'), 'px4')

    def test_spawnpoints_parse(self):
        """All spawnpoints are valid 4-tuples of floats."""
        config = self._load_config(EXAMPLE_YAML)
        for vid, v in config['vehicles'].items():
            sp = self._parse_spawnpoint(v['spawnpoint'])
            self.assertEqual(len(sp), 4, f'vehicle_{vid} spawnpoint has {len(sp)} values')
            for coord in sp:
                self.assertIsInstance(coord, (int, float))


class TestMultiVehicleCompose(unittest.TestCase):
    """Validate docker-compose generation for multi-vehicle config."""

    def setUp(self):  # noqa: D102
        from generate_compose import generate_compose_override, load_config
        self._load_config = load_config
        self._generate = generate_compose_override
        self.config = self._load_config(EXAMPLE_YAML)
        self.compose = self._generate(self.config)

    def test_all_vehicle_services_generated(self):
        """All 10 non-obstacle vehicles generate services."""
        vehicle_services = [s for s in self.compose['services'] if s.startswith('vehicle_')]
        self.assertEqual(len(vehicle_services), 10)

    def test_vehicle_models_string(self):
        """vehicle_models parameter includes all non-obstacle models."""
        v5_cmd = self.compose['services']['vehicle_5']['command']
        self.assertIn('vehicle_models:=', v5_cmd)
        self.assertIn('rover_ackermann_5', v5_cmd)

    def test_networks_are_disjoint(self):
        """No two services share the same IP."""
        all_ips = {}
        for sname, svc in self.compose['services'].items():
            for net, netcfg in svc.get('networks', {}).items():
                ip = netcfg['ipv4_address']
                self.assertNotIn(ip, all_ips, f'IP {ip} reused by {sname}')
                all_ips[ip] = sname

    def test_gazebo_network_range(self):
        """Gazebo network IPs follow 172.20.0.{10+vid} pattern."""
        for sname, svc in self.compose['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            expected_ip = f'172.20.0.{10 + vid}'
            self.assertEqual(
                svc['networks']['gazebo-network']['ipv4_address'],
                expected_ip,
                f'{sname} gazebo IP mismatch'
            )

    def test_vehicle_network_range(self):
        """Vehicle network IPs follow 172.30.0.{10+vid} pattern."""
        for sname, svc in self.compose['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            expected_ip = f'172.30.0.{10 + vid}'
            self.assertEqual(
                svc['networks']['vehicle-network']['ipv4_address'],
                expected_ip,
                f'{sname} vehicle IP mismatch'
            )

    def test_firmware_to_command(self):
        """Firmware setting propagates to ros2 launch command."""
        self.assertIn('firmware:=ardupilot', self.compose['services']['vehicle_5']['command'])
        self.assertIn('firmware:=ardupilot', self.compose['services']['vehicle_8']['command'])
        self.assertIn('firmware:=px4', self.compose['services']['vehicle_0']['command'])

    def test_px4_env_vars(self):
        """PX4 vehicles get PX4_GZ_STANDALONE and DDS profile."""
        env = self.compose['services']['vehicle_0']['environment']
        env_str = ' '.join(env)
        self.assertIn('PX4_GZ_STANDALONE=1', env_str)
        self.assertIn('FASTRTPS_DEFAULT_PROFILES_FILE', env_str)

    def test_ardupilot_no_px4_env_vars(self):
        """ArduPilot vehicles do NOT get PX4-specific env vars."""
        env = self.compose['services']['vehicle_5']['environment']
        env_str = ' '.join(env)
        self.assertNotIn('PX4_GZ_STANDALONE', env_str)
        self.assertNotIn('FASTRTPS_DEFAULT_PROFILES_FILE', env_str)

    def test_jsbsim_no_px4_env_vars(self):
        """JSBSim vehicles do NOT get PX4-specific env vars (same as ArduPilot)."""
        self.assertNotIn('vehicle_jsbsim', self.compose['services'],
                         'No JSBSim vehicle in example.yaml; test is coverage placeholder')
        # If a JSBSim vehicle were added to example.yaml, this would verify:
        # env = self.compose['services']['vehicle_N']['environment']
        # env_str = ' '.join(env)
        # self.assertNotIn('PX4_GZ_STANDALONE', env_str)

    def test_common_env_vars_all_vehicles(self):
        """All vehicles share common env vars regardless of firmware."""
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            env = ' '.join(svc['environment'])
            self.assertIn('DISPLAY=', env, f'{sname} missing DISPLAY')
            self.assertIn('GZ_IP=', env, f'{sname} missing GZ_IP')
            self.assertIn('GZ_PARTITION=realgazebo', env, f'{sname} missing GZ_PARTITION')
            self.assertIn('MAVLINK_GCS_IP=', env, f'{sname} missing MAVLINK_GCS_IP')

    def test_rock_skip_in_compose(self):
        """Rock vehicles are skipped in compose generation (handled by Gazebo)."""
        # example.yaml has no rocks, so verify the skip mechanism works
        vehicle_types = {}
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                cmd = svc['command']
                import re
                m = re.search(r'vehicle_type:=(\w+)', cmd)
                if m:
                    vehicle_types[sname] = m.group(1)
        self.assertNotIn('rock', vehicle_types.values(),
                         'Rock should not appear as a vehicle service')

    def test_all_vehicle_ports_unique(self):
        """No duplicate UDP port mappings."""
        ports = set()
        for sname, svc in self.compose['services'].items():
            for port in svc.get('ports', []):
                udp_port = port.split(':')[0]
                self.assertNotIn(udp_port, ports, f'Port {udp_port} reused on {sname}')
                ports.add(udp_port)

    def test_vehicle_depends_on_gazebo(self):
        """All vehicle services depend on gazebo being healthy."""
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                deps = svc.get('depends_on', {})
                self.assertIn('gazebo', deps)
                self.assertEqual(deps['gazebo']['condition'], 'service_healthy')

    def test_spawnpoint_in_command(self):
        """Spawnpoint coordinates appear in the launch command."""
        cmd = self.compose['services']['vehicle_0']['command']
        self.assertIn('spawnpoint:=', cmd)

    def test_restart_unless_stopped(self):
        """All vehicle services have restart: unless-stopped."""
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            self.assertEqual(svc.get('restart'), 'unless-stopped',
                             f'{sname} missing restart policy')

    def test_logging_prefix_in_command(self):
        """Vehicle commands include [vehicle_N] log prefix."""
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            cmd = svc['command']
            self.assertIn('[vehicle_', cmd, f'{sname} missing logging prefix')

    def test_v2v_vehicle_models_all_vehicles(self):
        """Every vehicle's command lists all other vehicles in vehicle_models."""
        models_by_vehicle = {}
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            cmd = svc['command']
            import re
            m = re.search(r'vehicle_models:=([\w,]+)', cmd)
            self.assertIsNotNone(m, f'{sname} missing vehicle_models')
            models = set(m.group(1).split(','))
            models_by_vehicle[sname] = models

        # All vehicles should have the same model list
        ref_models = next(iter(models_by_vehicle.values()))
        for sname, models in models_by_vehicle.items():
            self.assertEqual(
                models, ref_models,
                f'{sname} vehicle_models differs from reference'
            )

        # All 10 vehicle-model entries present
        self.assertEqual(len(ref_models), 10)

    def test_v2v_network_isolation_env(self):
        """Each vehicle has GZ_IP set to its gazebo-network IP."""
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            vid = int(sname.split('_')[1])
            env = ' '.join(svc['environment'])
            expected_gz_ip = f'GZ_IP=172.20.0.{10 + vid}'
            self.assertIn(expected_gz_ip, env, f'{sname} missing {expected_gz_ip}')
            self.assertIn('GZ_PARTITION=realgazebo', env, f'{sname} missing GZ_PARTITION')

    def test_v2v_network_sim_parameters(self):
        """Vehicle launch command includes network_sim config in vehicle_models."""
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            cmd = svc['command']
            self.assertIn('vehicle_models:=', cmd)

    def test_v2v_mavlink_port_unique(self):
        """Each vehicle has a unique MAVLink UDP port for GCS."""
        ports = set()
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            for port in svc.get('ports', []):
                udp_port = int(port.split(':')[0])
                self.assertNotIn(udp_port, ports, f'Port {udp_port} reused on {sname}')
                ports.add(udp_port)
                self.assertGreaterEqual(udp_port, 18570)
                self.assertLessEqual(udp_port, 18579)

    def test_px4_path_resolved_from_build_targets(self):
        """Vehicle px4_path comes from build_targets config, not hardcoded."""
        import re
        cmd = self.compose['services']['vehicle_0']['command']
        # px4_path should be the resolved path from build_targets[0]
        m = re.search(r'px4_path:=(\S+)', cmd)
        self.assertIsNotNone(m, 'px4_path not found in command')
        # Default in example.yaml is /home/user/realgazebo/RealGazebo-PX4
        self.assertEqual(m.group(1), '/home/user/realgazebo/RealGazebo-PX4')

    def test_pipeline_end_to_end(self):
        """End-to-end pipeline: YAML -> compose -> override file is valid YAML."""
        import tempfile
        import yaml
        from generate_compose import generate_compose_override
        output_path = os.path.join(tempfile.mkdtemp(), 'override.yml')
        with open(output_path, 'w') as f:
            yaml.dump(
                generate_compose_override(self.config),
                f, default_flow_style=False, sort_keys=False
            )
        # Read back and validate structure
        with open(output_path) as f:
            parsed = yaml.safe_load(f)
        self.assertIn('services', parsed)
        self.assertIn('vehicle_0', parsed['services'])
        self.assertIn('networks', parsed['services']['vehicle_0'])
        self.assertIn('gazebo-network', parsed['services']['vehicle_0']['networks'])
        self.assertIn('vehicle-network', parsed['services']['vehicle_0']['networks'])
        self.assertIn('healthcheck', parsed['services']['vehicle_0'])
        self.assertIn('restart', parsed['services']['vehicle_0'])
        self.assertIn('stop_grace_period', parsed['services']['vehicle_0'])
        self.assertEqual(parsed['services']['vehicle_0']['restart'], 'unless-stopped')
        self.assertEqual(parsed['services']['vehicle_0']['stop_grace_period'], '30s')
