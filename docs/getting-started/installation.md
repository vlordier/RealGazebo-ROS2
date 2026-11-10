# Installation

## Prerequisites

- **Docker** (24+)
- **Docker Compose v2**
- **Git** (2.40+)
- **4 CPU cores, 8GB RAM** (minimum for ARM64 native build)

## Clone

```bash
git clone --recursive https://github.com/vlordier/RealGazebo-ROS2.git
cd RealGazebo-ROS2

# Initialize all submodules
git submodule update --init --recursive
```

## Build Docker Image

### Option A: Base image (ROS2 + Gazebo only, ~10 min)
```bash
make build-base
```

### Option B: Full image (includes PX4 + ArduPilot, ~2 hours)
```bash
make build-full
```

## Install Dev Tools

```bash
make setup
```

This installs `ruff`, `mypy`, `pre-commit`, and configures git hooks.

## Verify Installation

```bash
make test     # Run all Python tests
make lint    # Check code style
make ps      # List Docker containers
```
