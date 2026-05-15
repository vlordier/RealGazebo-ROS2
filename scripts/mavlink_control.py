#!/usr/bin/env python3
"""Direct MAVLink control for ArduPilot SITL — no ROS2 or MAVROS needed.

Connects to ArduPilot via UDP MAVLink, sends arm/takeoff/land commands.
Usage:
    python3 mavlink_control.py arm --port 14550
    python3 mavlink_control.py takeoff --port 14550 --altitude 10
    python3 mavlink_control.py land --port 14550
"""

import argparse
import time

from pymavlink import mavutil


def connect(port: int = 14550, timeout: int = 10):
    """Connect to ArduPilot SITL via UDP."""
    conn = mavutil.mavlink_connection(f'udp:127.0.0.1:{port}', timeout=timeout)
    conn.wait_heartbeat(timeout=timeout)
    print(f'  Connected to system {conn.target_system}, component {conn.target_component}')
    return conn


def arm(conn):
    """Arm the vehicle."""
    conn.arducopter_arm()
    msg = conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if msg and msg.result == 0:
        print('  Armed successfully')
        return True
    print(f'  Arm failed (result={msg.result if msg else "timeout"})')
    return False


def takeoff(conn, altitude: float = 10.0):
    """Take off to given altitude."""
    conn.mav.command_long_send(
        conn.target_system,
        conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0,
        0,
        0,
        0,
        0,
        altitude,
    )
    msg = conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if msg and msg.result == 0:
        print(f'  Takeoff to {altitude}m accepted')
        return True
    print(f'  Takeoff failed (result={msg.result if msg else "timeout"})')
    return False


def land(conn):
    """Land the vehicle."""
    conn.mav.command_long_send(
        conn.target_system,
        conn.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )
    msg = conn.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if msg and msg.result == 0:
        print('  Land accepted')
        return True
    print(f'  Land failed (result={msg.result if msg else "timeout"})')
    return False


def set_params(conn, params: dict):
    """Set ArduPilot parameters via MAVLink PARAM_SET."""
    for name, value in params.items():
        # fmt: off
        conn.mav.param_set_send(conn.target_system, conn.target_component, name.encode(), value, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)  # noqa: E501
        # fmt: on
        time.sleep(0.5)
        print(f'  Set {name}={value}')


def main():
    parser = argparse.ArgumentParser(description='Direct MAVLink control for ArduPilot SITL')
    parser.add_argument(
        'command',
        choices=['arm', 'takeoff', 'land', 'set-params', 'all'],
        help='Command to execute',
    )
    parser.add_argument('--port', type=int, default=14550, help='MAVLink UDP port (default: 14550)')
    parser.add_argument('--altitude', type=float, default=10.0, help='Takeoff altitude in meters')
    parser.add_argument('--instance', type=int, default=0, help='Vehicle instance ID')

    args = parser.parse_args()

    if args.instance:
        args.port = 14550 + args.instance * 2

    conn = connect(port=args.port)

    if args.command == 'set-params' or args.command == 'all':
        ardupilot_params = {
            'SYSID_SW_MREV': 0,  # Skip RC check
            'SERVO1_FUNCTION': 33,  # Motor 1
            'SERVO2_FUNCTION': 34,  # Motor 2
            'SERVO3_FUNCTION': 35,  # Motor 3
            'SERVO4_FUNCTION': 36,  # Motor 4
            'FRAME_CLASS': 1,  # Quad frame
            'FRAME_TYPE': 1,  # X-configuration
        }
        set_params(conn, ardupilot_params)

    if args.command == 'arm' or args.command == 'all':
        arm(conn)

    if args.command == 'takeoff' or args.command == 'all':
        time.sleep(2)
        takeoff(conn, args.altitude)

    if args.command == 'land':
        land(conn)


if __name__ == '__main__':
    main()
