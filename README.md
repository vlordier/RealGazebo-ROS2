# RealGazebo-ROS2

Multi-vehicle simulation framework integrating **Gazebo Harmonic**, **ROS2 Jazzy**, **PX4 SITL**, **ArduPilot SITL**, **JSBSim**, **Unreal Engine 5**, and **dora-rs**.

[![CI](https://img.shields.io/github/actions/workflow/status/vlordier/RealGazebo-ROS2/ci.yml?branch=main)](https://github.com/vlordier/RealGazebo-ROS2/actions)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL3-blue.svg)](LICENSE)

## Overview

A production-grade simulation platform for multi-vehicle UAV research, bridging Gazebo physics with ROS2 middleware and supporting multiple flight stack backends.

## Key Features

- **Multi-Vehicle Support** — PX4, ArduPilot, and JSBSim in a single simulation
- **ROS2 Jazzy + Gazebo Harmonic** — Latest LTS stack, containerized for reproducibility
- **UE5 Integration** — Real-time pose/motor data streaming to Unreal Engine 5
- **dora-rs Data Pipeline** — Pydantic-validated dataflow for real-time analytics
- **Automated CI/CD** — Docker build, smoke tests, and documentation deployment

## Architecture

```mermaid
graph TB
    subgraph Sim["Simulation"]
        Gazebo["Gazebo Harmonic<br/>Physics + Rendering"]:::service
    end

    subgraph FlightStacks["Flight Control"]
        PX4["PX4 SITL<br/>uXRCE-DDS"]:::data
        AP["ArduPilot SITL<br/>MAVLink + MAVROS"]:::data
        JSB["JSBSim FDM<br/>Flight Dynamics"]:::data
    end

    subgraph Bridge["ROS2 Bridge"]
        Manager["Manager pkg<br/>ROS2 Bridge"]:::service
        DroneCtrl["Drone Controller<br/>Missions"]:::client
    end

    subgraph Streams["Data Streams"]
        UE5["UE5 Receiver<br/>UDP + Unreal"]:::service
        Dora["dora-rs<br/>Data Pipeline"]:::service
    end

    subgraph Tools["Tools"]
        NetSim["Network Sim<br/>V2V qdisc"]:::client
        ImgViewer["Image Viewer<br/>RTSP"]:::client
    end

    classDef service fill:#e3f2fd,stroke:#1976d2,stroke-width:2px;
    classDef data fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef client fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;

    Gazebo --> PX4 & AP & JSB
    PX4 --> Manager
    AP --> Manager
    JSB --> Manager
    Manager --> DroneCtrl
    Manager --> UE5
    Manager --> Dora
    Manager --> NetSim
    Manager --> ImgViewer
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

## Requirements

- **ROS2 Jazzy** + **Gazebo Harmonic** (Ubuntu 24.04)
- Python 3.10+ (3.12 recommended)
- Docker with Buildx
- **macOS**: `brew install --cask xquartz` + `xhost +localhost` for GUI

## Developer

```bash
make test        # Run all Python tests
make lint        # Run ruff linter
make up-dev      # Start with hot-reload
make clean       # Remove build artifacts
```

## License

GPL-3.0-only. See [LICENSE](LICENSE).
