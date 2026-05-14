# RealGazebo-ROS2 — Agent Guide

## Project Structure
- `src/realgazebo/` — ROS2 package: Gazebo plugins, launch files, SDF templates
- `src/network_sim/` — ROS2 package: V2V communication simulation (C++)
- `src/jsbsim_bridge/` — ROS2 package: JSBSim flight dynamics bridge
- `src/ardupilot_bridge/` — ROS2 package: ArduPilot MAVROS bridge
- `src/px4_msgs/` — Git submodule: PX4 ROS2 message definitions
- `src/ACSL-flightstack/` — Git submodule: ACSL flight stack
- `realgazebo-dora/` — dora-rs dataflow operators (Python)
- `scripts/` — generate_compose.py, quickstart.sh, smoke_test.sh
- `scripts/tests/` — Python unit tests
- `docker/` — Dockerfile.base (ROS2+Gazebo), Dockerfile (full: +PX4+ArduPilot)
- `.github/workflows/ci.yml` — CI/CD pipeline

## Testing Approach
- **Unit tests**: `python3 -m pytest scripts/tests/ -v -m "not integration"`
- **Integration tests**: `python3 -m pytest scripts/tests/ -v -m integration` (requires Docker)
- **Full suite**: `make test`
- **Smoke test**: `bash scripts/smoke_test.sh` (requires `make up`)

All commands run from project root. Python 3.10+ required for some test files.

## Key Conventions
- SDF templates use Jinja2 (`.sdf.jinja`), rendered at launch with firmware selection
- Firmware types: `px4`, `ardupilot`, `jsbsim` (validated by Pydantic)
- Vehicle config in YAML: `scripts/generate_compose.py` → `docker-compose.override.yml`
- Shared motor templates stored as `_x500_motors.sdf.jinja` (underscore prefix)
- Config key `build_targets` (not `px4_target`; the old name triggers DeprecationWarning)

## Tested Versions
- **ROS2**: Jazzy (Ubuntu 24.04 / Gazebo Harmonic)
- **PX4**: v1.16.1 (from `src/px4_msgs` submodule)
- **ArduPilot**: latest master (Copter 4.6+)
- **JSBSim**: 1.3.0 (pip)
- **Gazebo**: Harmonic (bundled with ROS2 Jazzy)
- **Python**: 3.10+ (CI tests on 3.10, 3.11, 3.12)
- **Docker**: 24.0+ with Buildx

## Common Tasks
- **One-command deploy**: `bash scripts/quickstart.sh`
- **Build base image**: `make build` (or `make build-full` for PX4+ArduPilot)
- **Start sim**: `make up`
- **Stop sim**: `make down`
- **Lint**: `make lint`
- **Type check**: `make typecheck`

## V2V Communication
- Network topology: `172.20.0.0/16` (gazebo), `172.30.0.0/16` (vehicle, internal)
- Each vehicle has `network_sim_node` with TC qdisc for latency/jitter/packet-loss simulation
- See `src/network_sim/README.md` for architecture details
