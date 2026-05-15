"""Tests for multi-vehicle V2V simulation stack.

Unit tests validate config loading, compose generation, and network topology.
Integration tests (marked @pytest.mark.integration) require Docker + running stack.
"""

import os
import re
import tempfile
import unittest

import pytest
import yaml

EXAMPLE_YAML = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'realgazebo', 'yaml', 'example.yaml'
)


class TestMultiVehicleConfig(unittest.TestCase):
    """Validate that example.yaml loads correctly with all 10 vehicles."""

    def setUp(self):
        from generate_compose import load_config

        self._config = load_config(EXAMPLE_YAML)

    def test_example_loads_all_vehicles(self):
        self.assertIn('vehicles', self._config)
        self.assertEqual(len(self._config['vehicles']), 10)

    def test_example_vehicle_types(self):
        types = {v['type'] for v in self._config['vehicles'].values()}
        expected = {'x500', 'x500_lidar_2d', 'lc_62', 'rover_ackermann', 'boat'}
        self.assertEqual(types, expected)

    def test_rover_has_ardupilot_firmware(self):
        self.assertEqual(self._config['vehicles'][5].get('firmware'), 'ardupilot')

    def test_boat_has_ardupilot_firmware(self):
        self.assertEqual(self._config['vehicles'][8].get('firmware'), 'ardupilot')

    def test_default_firmware_is_px4(self):
        for vid in [0, 1, 2, 3, 4, 6, 7, 9]:
            self.assertEqual(self._config['vehicles'][vid].get('firmware', 'px4'), 'px4')

    def test_spawnpoints_parse(self):
        from generate_compose import parse_spawnpoint

        for vid, v in self._config['vehicles'].items():
            sp = parse_spawnpoint(v['spawnpoint'])
            self.assertEqual(len(sp), 4, f'vehicle_{vid} spawnpoint has {len(sp)} values')
            for coord in sp:
                self.assertIsInstance(coord, (int, float))


class TestMultiVehicleCompose(unittest.TestCase):
    """Validate docker-compose generation for multi-vehicle config."""

    def setUp(self):
        from generate_compose import generate_compose_override, load_config

        self.compose = generate_compose_override(load_config(EXAMPLE_YAML))

    def test_all_vehicle_services_generated(self):
        vehicle_services = [s for s in self.compose['services'] if s.startswith('vehicle_')]
        self.assertEqual(len(vehicle_services), 10)

    def test_vehicle_models_string(self):
        v5_cmd = self.compose['services']['vehicle_5']['command']
        self.assertIn('vehicle_models:=', v5_cmd)
        self.assertIn('rover_ackermann_5', v5_cmd)

    def test_networks_are_disjoint(self):
        all_ips = {}
        for sname, svc in self.compose['services'].items():
            for _net, netcfg in svc.get('networks', {}).items():
                ip = netcfg['ipv4_address']
                self.assertNotIn(ip, all_ips, f'IP {ip} reused by {sname}')
                all_ips[ip] = sname

    def test_gazebo_network_range(self):
        for sname, svc in self.compose['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            self.assertEqual(
                svc['networks']['gazebo-network']['ipv4_address'], f'172.20.0.{10 + vid}'
            )

    def test_vehicle_network_range(self):
        for sname, svc in self.compose['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            self.assertEqual(
                svc['networks']['vehicle-network']['ipv4_address'], f'172.30.0.{10 + vid}'
            )

    def test_firmware_to_command(self):
        self.assertIn('firmware:=ardupilot', self.compose['services']['vehicle_5']['command'])
        self.assertIn('firmware:=ardupilot', self.compose['services']['vehicle_8']['command'])
        self.assertIn('firmware:=px4', self.compose['services']['vehicle_0']['command'])

    def test_px4_env_vars(self):
        env = ' '.join(self.compose['services']['vehicle_0']['environment'])
        self.assertIn('PX4_GZ_STANDALONE=1', env)
        self.assertIn('FASTRTPS_DEFAULT_PROFILES_FILE', env)

    def test_ardupilot_no_px4_env_vars(self):
        env = ' '.join(self.compose['services']['vehicle_5']['environment'])
        self.assertNotIn('PX4_GZ_STANDALONE', env)
        self.assertNotIn('FASTRTPS_DEFAULT_PROFILES_FILE', env)

    def test_common_env_vars_all_vehicles(self):
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            env = ' '.join(svc['environment'])
            self.assertIn('DISPLAY=', env, f'{sname} missing DISPLAY')
            self.assertIn('GZ_IP=', env, f'{sname} missing GZ_IP')
            self.assertIn('GZ_PARTITION=realgazebo', env, f'{sname} missing GZ_PARTITION')
            self.assertIn('MAVLINK_GCS_IP=', env, f'{sname} missing MAVLINK_GCS_IP')

    def test_rock_skip_in_compose(self):
        vehicle_types = {}
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                m = re.search(r'vehicle_type:=(\w+)', svc['command'])
                if m:
                    vehicle_types[sname] = m.group(1)
        self.assertNotIn(
            'rock', vehicle_types.values(), 'Rock should not appear as a vehicle service'
        )

    def test_all_vehicle_ports_unique(self):
        ports = set()
        for sname, svc in self.compose['services'].items():
            for port in svc.get('ports', []):
                udp_port = port.split(':')[0]
                self.assertNotIn(udp_port, ports, f'Port {udp_port} reused on {sname}')
                ports.add(udp_port)

    def test_vehicle_depends_on_gazebo(self):
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                self.assertEqual(svc['depends_on']['gazebo']['condition'], 'service_healthy')

    def test_spawnpoint_in_command(self):
        self.assertIn('spawnpoint:=', self.compose['services']['vehicle_0']['command'])

    def test_restart_unless_stopped(self):
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                self.assertEqual(
                    svc.get('restart'), 'unless-stopped', f'{sname} missing restart policy'
                )

    def test_logging_prefix_in_command(self):
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                self.assertIn('[vehicle_', svc['command'], f'{sname} missing logging prefix')

    def test_px4_path_resolved_from_build_targets(self):
        cmd = self.compose['services']['vehicle_0']['command']
        m = re.search(r'px4_path:=(\S+)', cmd)
        self.assertIsNotNone(m, 'px4_path not found')
        self.assertEqual(m.group(1), '/home/user/realgazebo/RealGazebo-PX4')

    def test_healthcheck_configured(self):
        for sname, svc in self.compose['services'].items():
            if sname.startswith('vehicle_'):
                hc = svc.get('healthcheck', {})
                self.assertIn('test', hc, f'{sname} missing healthcheck')
                self.assertEqual(hc.get('retries'), 10)
                self.assertEqual(hc.get('interval'), '15s')
                self.assertEqual(hc.get('start_period'), '120s')

    def test_v2v_vehicle_models_all_vehicles(self):
        models_by_vehicle = {}
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            m = re.search(r'vehicle_models:=([\w,]+)', svc['command'])
            self.assertIsNotNone(m, f'{sname} missing vehicle_models')
            models_by_vehicle[sname] = set(m.group(1).split(','))
        ref_models = next(iter(models_by_vehicle.values()))
        for sname, models in models_by_vehicle.items():
            self.assertEqual(models, ref_models, f'{sname} vehicle_models differs')
        self.assertEqual(len(ref_models), 10)

    def test_v2v_network_isolation_env(self):
        for sname, svc in self.compose['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            vid = int(sname.split('_')[1])
            env = ' '.join(svc['environment'])
            self.assertIn(f'GZ_IP=172.20.0.{10 + vid}', env, f'{sname} missing GZ_IP')

    def test_v2v_mavlink_port_unique(self):
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

    def test_pipeline_end_to_end(self):
        """YAML -> compose -> validate output is valid YAML with expected structure."""
        from generate_compose import generate_compose_override, load_config

        output_path = os.path.join(tempfile.mkdtemp(), 'override.yml')
        with open(output_path, 'w') as f:
            yaml.dump(
                generate_compose_override(load_config(EXAMPLE_YAML)),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
        with open(output_path) as f:
            parsed = yaml.safe_load(f)
        self.assertIn('services', parsed)
        s0 = parsed['services']['vehicle_0']
        self.assertIn('gazebo-network', s0['networks'])
        self.assertIn('vehicle-network', s0['networks'])
        self.assertIn('healthcheck', s0)
        self.assertEqual(s0['restart'], 'unless-stopped')
        self.assertEqual(s0['stop_grace_period'], '30s')


class TestMultiVehicleIntegration(unittest.TestCase):
    """Integration tests that require Docker + running stack.
    Run with: python -m pytest scripts/tests/test_multi_vehicle.py -m integration
    """

    @pytest.mark.integration
    def test_docker_reachable(self):
        import subprocess

        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, 'Docker daemon not reachable')

    @pytest.mark.integration
    def test_gazebo_container_running(self):
        import subprocess

        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        self.assertTrue(any('gazebo' in n for n in names), f'No gazebo container. Found: {names}')

    @pytest.mark.integration
    def test_vehicle_containers_running(self):
        import subprocess

        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        self.assertGreater(
            sum(1 for n in names if 'vehicle_' in n), 0, f'No vehicle containers. Found: {names}'
        )
