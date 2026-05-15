#!/usr/bin/env python3
"""Generate docker-compose.override.yml from RealGazebo YAML configuration.

Called by quickstart.sh or used directly:
    python3 scripts/generate_compose.py src/realgazebo/yaml/example.yaml
"""

import argparse
import ast
import os
import sys
import warnings
from typing import Any

import yaml
from pydantic import BaseModel, Field

SUPPORT_OBSTACLE = ['rock']


class VehicleEntry(BaseModel):
    """Validated vehicle entry from YAML configuration."""

    type: str = Field(pattern=r'^(x500|x500_lidar_2d|lc_62|rover_ackermann|boat|rock)$')
    firmware: str = Field(default='ardupilot', pattern=r'^(px4|ardupilot|jsbsim)$')
    build_target: int = Field(default=0, ge=0)
    spawnpoint: str = Field(default='(0,0,0,0)', pattern=r'^\(.*\)$')


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate docker-compose.override.yml from vehicle configuration'
    )
    parser.add_argument('config_file', nargs='?', help='Path to vehicle YAML configuration file')
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='Output path for docker-compose.override.yml (default: project root)',
    )
    parser.add_argument(
        '--unreal-ip',
        default='host.docker.internal',
        help='Unreal Engine server IP (default: host.docker.internal)',
    )
    parser.add_argument(
        '--unreal-port',
        default='5005',
        help='Unreal Engine server port (default: 5005)',
    )
    parser.add_argument(
        '--image', default='realgazebo:full', help='Docker image tag (default: realgazebo:full)'
    )
    parser.add_argument(
        '--world',
        default='c-track',
        choices=['c-track', 'urban', 'vils'],
        help='World type (default: c-track)',
    )
    parser.add_argument(
        '--headless', action='store_true', default=True, help='Run in headless mode (default: true)'
    )
    parser.add_argument(
        '--gui', action='store_true', help='Run with Gazebo GUI (disables headless)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate YAML config and exit (dry-run, no file written)',
    )
    return parser.parse_args(argv)


def load_config(config_path: str) -> dict:
    """Load and validate vehicle configuration from YAML file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    if config is None:
        raise ValueError(f'Empty or invalid YAML file: {config_path}')

    if 'px4_target' in config and 'build_targets' not in config:
        warnings.warn(
            "YAML key 'px4_target' is deprecated, use 'build_targets' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        config['build_targets'] = config.pop('px4_target')

    vehicles = config.get('vehicles', {})
    for vid, v in vehicles.items():
        if not isinstance(v, dict):
            raise ValueError(f'Vehicle {vid}: expected a mapping, got {type(v).__name__}')
        if 'type' not in v:
            raise ValueError(f"Vehicle {vid}: missing required field 'type'")
        VehicleEntry(**v)
    return config


def parse_spawnpoint(spawnpoint_str: Any) -> list[float]:
    """Parse spawnpoint from string tuple format: (x, y, z, yaw)"""
    try:
        if isinstance(spawnpoint_str, str):
            parsed = ast.literal_eval(spawnpoint_str)
            return list(parsed)
        elif isinstance(spawnpoint_str, (list, tuple)):
            return list(spawnpoint_str)
    except (ValueError, SyntaxError, TypeError, MemoryError):
        pass
    raise ValueError(f'Invalid spawnpoint format: {spawnpoint_str}')


def _is_vehicle(vtype: Any) -> bool:
    """Check if a vehicle type is a real vehicle (not an obstacle)."""
    return vtype not in SUPPORT_OBSTACLE


def generate_compose_override(
    config: dict,
    unreal_ip: str = 'host.docker.internal',
    unreal_port: str = '5005',
    world: str = 'c-track',
    headless: bool = True,
    image: str = 'realgazebo:base',
) -> dict:
    """Generate docker-compose.override.yml content from YAML config.

    Two lightweight passes: first collects metadata and builds the model list,
    second builds full service dicts (needs the complete model list for commands).
    """
    build_targets = config.get('build_targets', {}) or {}
    vehicles = config.get('vehicles', {})

    workspace = os.environ.get('WORKSPACE', '/home/user/realgazebo/RealGazebo-ROS2')
    mem_limit = os.environ.get('VEHICLE_MEMORY', '4G')

    vehicle_models = []
    vmeta = []
    for vid, vehicle in vehicles.items():
        vid = int(vid)
        vtype = vehicle.get('type')
        if not _is_vehicle(vtype):
            print(
                f"  [SKIP] vehicle_{vid}: type '{vtype}' is an obstacle, handled by Gazebo container"
            )
            continue
        vehicle_models.append(f'{vtype}_{vid}')
        vmeta.append(
            {
                'vid': vid,
                'vtype': vtype,
                'v_firmware': vehicle.get('firmware', 'px4'),
                'v_build_target': vehicle.get('build_target', 0),
                'spawnpoint': parse_spawnpoint(vehicle.get('spawnpoint')),
                'service_name': f'vehicle_{vid}',
                'vehicle_gazebo_ip': f'172.20.0.{10 + vid}',
                'vehicle_network_ip': f'172.30.0.{10 + vid}',
            }
        )

    vehicle_models_str = ','.join(vehicle_models)
    compose: dict = {'services': {}}

    for m in vmeta:
        px4_path = build_targets.get(m['v_build_target'], '/home/user/realgazebo/RealGazebo-PX4')
        spawnpoint_str = ','.join(map(str, m['spawnpoint']))

        env_vars = [
            'DISPLAY=${DISPLAY:-:0}',
            'QT_X11_NO_MITSHM=1',
            f'GZ_IP={m["vehicle_gazebo_ip"]}',
            'GZ_PARTITION=realgazebo',
            'LOCAL_USER_ID=${LOCAL_USER_ID:-1000}',
            'MAVLINK_GCS_IP=${MAVLINK_GCS_IP:-172.17.0.1}',
        ]
        if m['v_firmware'] == 'px4':
            env_vars.append('PX4_GZ_STANDALONE=1')
            env_vars.append(
                f'FASTRTPS_DEFAULT_PROFILES_FILE=/tmp/dds_profiles/px4_participant_{m["vid"]}.xml'
            )

        compose['services'][m['service_name']] = {
            'image': image,
            'container_name': m['service_name'],
            'hostname': m['service_name'],
            'privileged': True,
            'environment': env_vars,
            'volumes': ['/tmp/.X11-unix:/tmp/.X11-unix'],
            'networks': {
                'gazebo-network': {'ipv4_address': m['vehicle_gazebo_ip']},
                'vehicle-network': {'ipv4_address': m['vehicle_network_ip']},
            },
            'extra_hosts': ['host.docker.internal:host-gateway'],
            'ports': [f'{18570 + m["vid"]}:{18570 + m["vid"]}/udp'],
            'depends_on': {'gazebo': {'condition': 'service_healthy'}},
            'healthcheck': {
                'test': [
                    'CMD-SHELL',
                    f'source /opt/ros/jazzy/setup.bash && timeout 5 ros2 topic list 2>/dev/null | grep -q /world/{world}/clock || exit 1',
                ],
                'interval': '15s',
                'timeout': '10s',
                'retries': 10,
                'start_period': '120s',
            },
            'restart': 'unless-stopped',
            'stop_grace_period': '30s',
            'command': (
                f'bash -c "exec > >(sed \\"s/^/[vehicle_{m["vid"]}] /\\") 2>&1; '
                f'sleep $(({m["vid"]} * 5)); '
                f'source /opt/ros/jazzy/setup.bash && '
                f'source {workspace}/install/setup.bash && '
                f'ros2 launch realgazebo vehicle.launch.py '
                f'instance_id:={m["vid"]} vehicle_type:={m["vtype"]} firmware:={m["v_firmware"]} '
                f'spawnpoint:={spawnpoint_str} px4_path:={px4_path} '
                f'unreal_ip:={unreal_ip} unreal_port:={unreal_port} '
                f'vehicle_models:={vehicle_models_str}"'
            ),
            'deploy': {'resources': {'limits': {'memory': mem_limit}}},
        }

    return compose


def main() -> None:
    args = parse_args()

    # --validate: dry-run, just validate the config
    if args.validate:
        if not args.config_file:
            print('Usage: generate_compose.py <config_file> --validate')
            sys.exit(1)
        config = load_config(args.config_file)
        print(f"Config '{args.config_file}' is valid.")
        print(f'  - {len(config.get("vehicles", {}))} vehicle(s) defined')
        return

    if not args.config_file:
        print('Error: config_file is required (use --validate for dry-run)')
        sys.exit(1)

    headless = not args.gui if args.gui else args.headless

    if args.output_file:
        output_path = args.output_file
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_path = os.path.join(project_root, 'docker-compose.override.yml')

    config = load_config(args.config_file)

    # Warn if ArduPilot/JSBSim firmware is requested but using the base image
    has_px4 = any(v.get('firmware') == 'px4' for v in config.get('vehicles', {}).values())
    has_jsbsim = any(v.get('firmware') == 'jsbsim' for v in config.get('vehicles', {}).values())
    if has_px4 and 'full' not in args.image:
        print('  [WARN] PX4 firmware requires the full image (realgazebo:full).')
        print(f'         Current: {args.image}')
    if has_jsbsim and 'jsbsim' not in args.image:
        pass  # JSBSim is pip-installable, no image constraint

    compose = generate_compose_override(
        config,
        unreal_ip=args.unreal_ip,
        unreal_port=args.unreal_port,
        world=args.world,
        headless=headless,
        image=args.image,
    )

    with open(output_path, 'w') as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    vehicles = config.get('vehicles', {})
    vehicle_count = sum(1 for v in vehicles.values() if _is_vehicle(v.get('type')))
    print(f'Generated {output_path}')
    print(f'  - {vehicle_count} vehicle(s) configured:')
    for vid, v in sorted(vehicles.items()):
        if _is_vehicle(v.get('type')):
            mavlink_port = 18570 + int(vid)
            print(
                f'    - vehicle_{vid}: {v["type"]} MAVLink→:{mavlink_port} at {v.get("spawnpoint", "(0,0,0,0)")}'
            )
    print('\nTo start the simulation:')
    print(f'  cd {os.path.dirname(output_path)}')
    print('  docker compose up -d')


if __name__ == '__main__':
    main()
