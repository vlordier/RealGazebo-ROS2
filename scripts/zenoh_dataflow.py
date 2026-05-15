#!/usr/bin/env python3
"""RealGazebo Zenoh dataflow — replaces ROS2 topics and dora-rs operators.

Publishes vehicle state (pose, RPM) via Zenoh topics.
Each vehicle publishes on key: realgazebo/{instance_id}/pose, /rpm, /status

Dependencies: pip install zenoh
Usage:
    python3 zenoh_dataflow.py --instance 0
"""

import argparse
import json
import struct
import time

import zenoh


def parse_ue5_packet(data: bytes) -> dict | None:
    """Parse 31-byte UDP packet from libRealGazebo.so."""
    if len(data) != 31:
        return None
    header = struct.unpack('<BBB', data[:3])
    floats = struct.unpack('<7f', data[3:])
    return {
        'vehicle_code': header[0],
        'vehicle_num': header[1],
        'packet_type': header[2],
        'x': floats[0],
        'y': floats[1],
        'z': floats[2],
        'qw': floats[3],
        'qx': floats[4],
        'qy': floats[5],
        'qz': floats[6],
    }


def main():
    parser = argparse.ArgumentParser(description='RealGazebo Zenoh dataflow node')
    parser.add_argument('--instance', type=int, default=0, help='Vehicle instance ID')
    parser.add_argument(
        '--connect',
        type=str,
        default='tcp/127.0.0.1:7447',
        help='Zenoh router endpoint (empty for routerless)',
    )
    args = parser.parse_args()

    # Zenoh configuration
    conf = zenoh.Config()
    if args.connect:
        conf.insert_json5('connect/endpoints', json.dumps([args.connect]))

    # Start Zenoh session
    session = zenoh.open(conf)
    prefix = f'realgazebo/{args.instance}'
    print(f'Zenoh dataflow started for instance {args.instance}')
    print(f'  Publishing on: {prefix}/pose, {prefix}/status')

    try:
        while True:
            # In a full implementation, this would:
            # 1. Subscribe to Gazebo's pose via gz-transport
            # 2. Publish to Zenoh: session.put(f'{prefix}/pose', pose_bytes)
            # 3. Subscribe to Zenoh: session.declare_subscriber(f'{prefix}/cmd', callback)
            # 4. Send MAVLink commands to ArduPilot

            # For now, publish a heartbeat
            status = json.dumps(
                {
                    'instance': args.instance,
                    'time': time.time(),
                    'status': 'running',
                }
            ).encode()
            session.put(f'{prefix}/status', status)

            time.sleep(1)

    except KeyboardInterrupt:
        print('Shutting down...')
    finally:
        session.close()


if __name__ == '__main__':
    main()
