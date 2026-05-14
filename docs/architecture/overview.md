# Architecture Overview

## Layers

```
┌─────────────────────────────────────────────────────┐
│               Unreal Engine 5 (Optional)             │
│  UDP ← RealGazebo.so (pose, motors, servos)         │
│  RTSP → image_receiver_node (camera streams)        │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              dora-rs Dataflow (Optional)              │
│  ros2_bridge operator → Pydantic models → outputs    │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              ROS2 Jazzy Middleware                    │
│  Topics: /vehicle{N}/fmu/*, /clock, /diagnostics     │
│  Services: /world/test/create (Gazebo entity spawn)  │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              Gazebo Harmonic Simulator                │
│  gz-sim8 physics + rendering                         │
│  Worlds: c-track, urban, vils                        │
└────────────────────────┬────────────────────────────┘
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
┌──────────┐      ┌──────────┐      ┌──────────────┐
│  PX4     │      │ArduPilot │      │   JSBSim     │
│ SITL     │      │  SITL    │      │    FDM       │
│ uXRCE-   │      │ MAVLink  │      │  ROS2 topics │
│ DDS      │      │ →MAVROS  │      │  →Gazebo vis │
└──────────┘      └──────────┘      └──────────────┘
```

## Container Architecture

| Container | Purpose | Base Image |
|-----------|---------|------------|
| `gazebo` | Physics + rendering + ROS2 bridge | `realgazebo:base` |
| `vehicle_N` | PX4/ArduPilot SITL + control nodes | `realgazebo:base` |
| `dora` | dora-rs dataflow (optional) | `realgazebo:base` |
