# Changelog
All notable changes to RealGazebo-ROS2 are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- ARM64 native Docker support (Apple Silicon)
- JSBSim flight dynamics model bridge (59 aircraft, clock sync)
- ArduPilot SITL support with MAVROS ROS2 bridge
- dora-rs dataflow alongside ROS2 (Pydantic v2 models)
- UE5 UDP contract models (VehiclePose, MotorRPM, SimReset)
- V2V diagnostics publisher for network_sim
- Multi-vehicle integration test
- Pre-commit hooks, ruff linter, mypy type checker
- CI/CD pipeline (GitHub Actions)
- Sphinx documentation with ReadTheDocs theme

### Fixed
- x86_64 QEMU emulation crash on ARM Mac → native ARM64 build
- c-track world STL mesh download failure → fallback STL generation
- Ignored bare `except:` in parse_spawnpoint
- Pipeline safety: docker-compose.dev.yml hot-reload mounts
- Code quality: 145 lint issues auto-fixed (imports, unused imports)
