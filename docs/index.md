# RealGazebo-ROS2

Multi-vehicle simulation framework integrating **Gazebo Harmonic**, **ROS2 Jazzy**,
**PX4 SITL**, **ArduPilot SITL**, **JSBSim**, **Unreal Engine 5**, and **dora-rs**.

## Quick Start

```bash
git clone --recursive https://github.com/vlordier/RealGazebo-ROS2.git
cd RealGazebo-ROS2
make setup          # Install dev tools + pre-commit hooks
make build-base     # Build base Docker image
make up             # Start simulation
make test           # Run all tests
```

## Supported Firmware

| Firmware | Status | Communication | Use Case |
|----------|--------|--------------|----------|
| PX4 | ✅ Production | uXRCE-DDS → ROS2 | Multi-rotor, VTOL, rover, boat |
| ArduPilot | ✅ Beta | MAVLink → MAVROS | Fixed-wing, copter, rover |
| JSBSim | ✅ Beta | ROS2 topics direct | High-fidelity flight dynamics |

## Architecture

```
Gazebo Simulator ──ros_gz_bridge──▶ ROS2 ────dora-rs dataflow
       ▲                               │
       │                               ├── RealGazebo.so ──UDP──▶ UE5
       │                               └── network_sim (V2V)
       │
       └── PX4 / ArduPilot / JSBSim (vehicle containers)
```
