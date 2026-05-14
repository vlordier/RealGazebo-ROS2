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


class TestMultiVehicleIntegration(unittest.TestCase):
    """Integration tests that require Docker + running stack.

    Run with: python -m pytest scripts/tests/test_multi_vehicle.py -m integration
    """

    @pytest.mark.integration
    def test_docker_reachable(self):
        """Docker daemon must be running."""
        import subprocess
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, 'Docker daemon not reachable')

    @pytest.mark.integration
    @pytest.mark.integration
    def test_gazebo_container_running(self):
        """Gazebo container must be running."""
        import subprocess
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        self.assertTrue(
            any('gazebo' in n for n in names),
            f'No gazebo container running. Found: {names}'
        )

    @pytest.mark.integration
    def test_vehicle_containers_running(self):
        """At least one vehicle_N container must be running."""
        import subprocess
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        vehicle_count = sum(1 for n in names if 'vehicle_' in n)
        self.assertGreater(
            vehicle_count, 0,
            f'No vehicle containers running. Found: {names}'
        )


if __name__ == '__main__':
    unittest.main()
