# RealGazebo-ROS2

Multi-vehicle simulation framework integrating **Gazebo Harmonic**, **ROS2 Jazzy**, **PX4 SITL**, **ArduPilot SITL**, **JSBSim**, **Unreal Engine 5**, and **dora-rs**.

## Architecture

```
                    ┌──────────────────────────────────┐
                    │  Gazebo Simulator                │
                    │  (physics + rendering)           │
                    └────────┬────────┬────────┬───────┘
                             │        │        │
              ┌──────────────┘        │        └──────────────┐
              ▼                      ▼                       ▼
       ┌───────────┐        ┌──────────────┐        ┌──────────────┐
       │ PX4 SITL  │        │ ArduPilot    │        │ JSBSim FDM   │
       │ uXRCE-DDS │        │ MAVLink→MAVROS│        │ ROS2 topics  │
       │ → ROS2    │        │ → ROS2       │        │ → Gazebo vis │
       └───────────┘        └──────────────┘        └──────────────┘
              │                      │                       │
              └──────────────────────┴───────────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ RealGazebo.so     │
                            │ UDP → UE5        │
                            │ (pose, motors)    │
                            └──────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ dora-rs dataflow │
                            │ (Pydantic models)│
                            └──────────────────┘
```

## Quick Start

```bash
# One-command setup and run (recommended)
bash scripts/quickstart.sh

# Or step by step:
make setup          # Install dev tools + pre-commit hooks
make build          # Build base Docker image
make up             # Start simulation
make test           # Run all tests
make smoke-test     # Verify system is healthy
```

## Vehicle Config

```yaml
vehicles:
  0:
    type: x500
    firmware: px4        # px4, ardupilot, or jsbsim
    build_target: 0
    spawnpoint: (0, 0, 0, 0)
```

## Packages

| Package | Language | Purpose |
|---------|----------|---------|
| `realgazebo` | C++ | Gazebo plugins, SDF models, launch files |
| `manager` | Python | PX4 ROS2 bridge, keyboard controller |
| `drone_controller` | Python | Autonomous mission execution |
| `image_viewer` | Python | RTSP camera stream viewer |
| `network_sim` | C++ | V2V communication simulation (TC qdisc) |
| `jsbsim_bridge` | Python | JSBSim flight dynamics ROS2 bridge |
| `ardupilot_bridge` | Python | ArduPilot MAVROS ROS2 bridge |
| `dora-rs` dataflow | Python | Pydantic-validated data pipeline |

## Requirements

- **ROS2 Jazzy** + **Gazebo Harmonic** (tested on Ubuntu 24.04)
- Python 3.10+ (3.12 recommended)
- Docker with Buildx (for containerized simulation)
- **macOS users**: Gazebo GUI requires XQuartz for X11 forwarding.
  Install with `brew install --cask xquartz`, then run:
  ```bash
  HEADLESS=false xhost +localhost make up
  ```

## Developer

```bash
make test        # Run all Python tests
make lint        # Run ruff linter
make up-dev      # Start with hot-reload mounts
make clean       # Remove build artifacts
```

## License

GPL-3.0-only. See [LICENSE](LICENSE).
