"""Tests for multi-vehicle V2V simulation stack.

Unit tests validate config loading, compose generation, and network topology.
Integration tests (marked @pytest.mark.integration) require Docker + running stack.
"""

import os
import re
import tempfile

import pytest
import yaml


class TestMultiVehicleConfig:
    """Validate that example.yaml loads correctly with all 10 vehicles.
    Uses the `example_config` session-scoped fixture from conftest.py.
    """

    def test_example_loads_all_vehicles(self, example_config):
        assert 'vehicles' in example_config
        assert len(example_config['vehicles']) == 10

    def test_example_vehicle_types(self, example_config):
        types = {v['type'] for v in example_config['vehicles'].values()}
        assert types == {'x500', 'x500_lidar_2d', 'lc_62', 'rover_ackermann', 'boat'}

    def test_rover_has_ardupilot_firmware(self, example_config):
        assert example_config['vehicles'][5].get('firmware') == 'ardupilot'

    def test_boat_has_ardupilot_firmware(self, example_config):
        assert example_config['vehicles'][8].get('firmware') == 'ardupilot'

    def test_default_firmware_is_ardupilot(self, example_config):
        """Vehicles without explicit firmware now default to ardupilot."""
        for vid in [0, 1, 2, 3, 4, 6, 7, 9]:
            assert example_config['vehicles'][vid].get('firmware', 'ardupilot') == 'ardupilot'

    def test_spawnpoints_parse(self, example_config):
        from generate_compose import parse_spawnpoint

        for vid, v in example_config['vehicles'].items():
            sp = parse_spawnpoint(v['spawnpoint'])
            assert len(sp) == 4, f'vehicle_{vid} spawnpoint has {len(sp)} values'
            assert all(isinstance(c, (int, float)) for c in sp)


class TestMultiVehicleCompose:
    """Validate docker-compose generation for multi-vehicle config.
    Uses the `compose_override` session-scoped fixture from conftest.py.
    """

    def test_all_vehicle_services_generated(self, compose_override):
        services = [s for s in compose_override['services'] if s.startswith('vehicle_')]
        assert len(services) == 10

    def test_vehicle_models_string(self, compose_override):
        cmd = compose_override['services']['vehicle_5']['command']
        assert 'vehicle_models:=' in cmd
        assert 'rover_ackermann_5' in cmd

    def test_networks_are_disjoint(self, compose_override):
        all_ips = {}
        for sname, svc in compose_override['services'].items():
            for netcfg in svc.get('networks', {}).values():
                ip = netcfg['ipv4_address']
                assert ip not in all_ips, f'IP {ip} reused by {sname}'
                all_ips[ip] = sname

    def test_gazebo_network_range(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            assert svc['networks']['gazebo-network']['ipv4_address'] == f'172.20.0.{10 + vid}'

    def test_vehicle_network_range(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if 'vehicle_' not in sname:
                continue
            vid = int(sname.split('_')[1])
            assert svc['networks']['vehicle-network']['ipv4_address'] == f'172.30.0.{10 + vid}'

    def test_firmware_to_command(self, compose_override):
        assert 'firmware:=ardupilot' in compose_override['services']['vehicle_5']['command']
        assert 'firmware:=ardupilot' in compose_override['services']['vehicle_8']['command']
        assert 'firmware:=px4' in compose_override['services']['vehicle_0']['command']

    def test_px4_env_vars(self, compose_override):
        env = ' '.join(compose_override['services']['vehicle_0']['environment'])
        assert 'PX4_GZ_STANDALONE=1' in env
        assert 'FASTRTPS_DEFAULT_PROFILES_FILE' in env

    def test_ardupilot_no_px4_env_vars(self, compose_override):
        env = ' '.join(compose_override['services']['vehicle_5']['environment'])
        assert 'PX4_GZ_STANDALONE' not in env
        assert 'FASTRTPS_DEFAULT_PROFILES_FILE' not in env

    def test_common_env_vars_all_vehicles(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            env = ' '.join(svc['environment'])
            assert 'DISPLAY=' in env, f'{sname} missing DISPLAY'
            assert 'GZ_IP=' in env, f'{sname} missing GZ_IP'
            assert 'GZ_PARTITION=realgazebo' in env, f'{sname} missing GZ_PARTITION'
            assert 'MAVLINK_GCS_IP=' in env, f'{sname} missing MAVLINK_GCS_IP'

    def test_rock_skip_in_compose(self, compose_override):
        types = {}
        for sname, svc in compose_override['services'].items():
            if sname.startswith('vehicle_'):
                m = re.search(r'vehicle_type:=(\w+)', svc['command'])
                if m:
                    types[sname] = m.group(1)
        assert 'rock' not in types.values(), 'Rock should not appear as a vehicle service'

    def test_all_vehicle_ports_unique(self, compose_override):
        ports = set()
        for sname, svc in compose_override['services'].items():
            for port in svc.get('ports', []):
                p = port.split(':')[0]
                assert p not in ports, f'Port {p} reused on {sname}'
                ports.add(p)

    def test_vehicle_depends_on_gazebo(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if sname.startswith('vehicle_'):
                assert svc['depends_on']['gazebo']['condition'] == 'service_healthy'

    def test_spawnpoint_in_command(self, compose_override):
        assert 'spawnpoint:=' in compose_override['services']['vehicle_0']['command']

    def test_restart_unless_stopped(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if sname.startswith('vehicle_'):
                assert svc.get('restart') == 'unless-stopped', f'{sname} missing restart policy'

    def test_logging_prefix_in_command(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if sname.startswith('vehicle_'):
                assert '[vehicle_' in svc['command'], f'{sname} missing logging prefix'

    def test_px4_path_resolved_from_build_targets(self, compose_override):
        m = re.search(r'px4_path:=(\S+)', compose_override['services']['vehicle_0']['command'])
        assert m is not None, 'px4_path not found'
        assert m.group(1) == '/home/user/realgazebo/RealGazebo-PX4'

    def test_healthcheck_configured(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if sname.startswith('vehicle_'):
                hc = svc.get('healthcheck', {})
                assert 'test' in hc, f'{sname} missing healthcheck'
                assert hc.get('retries') == 10
                assert hc.get('interval') == '15s'
                assert hc.get('start_period') == '120s'

    def test_v2v_vehicle_models_all_vehicles(self, compose_override):
        models = {}
        for sname, svc in compose_override['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            m = re.search(r'vehicle_models:=([\w,]+)', svc['command'])
            assert m is not None, f'{sname} missing vehicle_models'
            models[sname] = set(m.group(1).split(','))
        ref = next(iter(models.values()))
        for sname, m in models.items():
            assert m == ref, f'{sname} vehicle_models differs'
        assert len(ref) == 10

    def test_v2v_network_isolation_env(self, compose_override):
        for sname, svc in compose_override['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            vid = int(sname.split('_')[1])
            env = ' '.join(svc['environment'])
            assert f'GZ_IP=172.20.0.{10 + vid}' in env, f'{sname} missing GZ_IP'

    def test_v2v_mavlink_port_unique(self, compose_override):
        ports = set()
        for sname, svc in compose_override['services'].items():
            if not sname.startswith('vehicle_'):
                continue
            for port in svc.get('ports', []):
                p = int(port.split(':')[0])
                assert p not in ports, f'Port {p} reused on {sname}'
                ports.add(p)
                assert 18570 <= p <= 18579

    def test_pipeline_end_to_end(self, example_config):
        """YAML -> compose -> validate output is valid YAML with expected structure."""
        from generate_compose import generate_compose_override

        output_path = os.path.join(tempfile.mkdtemp(), 'override.yml')
        with open(output_path, 'w') as f:
            yaml.dump(
                generate_compose_override(example_config),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
        with open(output_path) as f:
            parsed = yaml.safe_load(f)
        assert 'services' in parsed
        s0 = parsed['services']['vehicle_0']
        assert 'gazebo-network' in s0['networks']
        assert 'vehicle-network' in s0['networks']
        assert 'healthcheck' in s0
        assert s0['restart'] == 'unless-stopped'
        assert s0['stop_grace_period'] == '30s'


@pytest.mark.integration
class TestMultiVehicleIntegration:
    """Integration tests requiring Docker + running stack.
    Run with: python -m pytest scripts/tests/ -m integration
    """

    def test_docker_reachable(self):
        import subprocess

        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        assert result.returncode == 0, 'Docker daemon not reachable'

    def test_gazebo_container_running(self):
        import subprocess

        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        assert any('gazebo' in n for n in names), f'No gazebo container. Found: {names}'

    def test_vehicle_containers_running(self):
        import subprocess

        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        assert sum(1 for n in names if 'vehicle_' in n) > 0, (
            f'No vehicle containers. Found: {names}'
        )
