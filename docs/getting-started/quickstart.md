# Quick Start

## 1. Start the Simulation

```bash
make up
```

This generates `docker-compose.override.yml` from the example config and starts all containers.

## 2. Monitor Startup

```bash
make logs     # Follow all container logs
docker compose ps  # Check container status
```

Gazebo takes ~30-60 seconds to load the world.

## 3. Control Vehicles

Open a new terminal:

```bash
# Send commands to vehicle 0
ros2 topic pub /vehicle1/manager/in/main_cmd std_msgs/String "data: ARM"
ros2 topic pub /vehicle1/manager/in/main_cmd std_msgs/String "data: OFFBOARD"
```

## 4. View Camera Streams

```bash
# View camera feed from vehicle 0 (requires display)
docker exec -it gazebo bash -c "source /opt/ros/jazzy/setup.bash && ros2 run image_viewer image_viewer --ros-args -p vehicle_num:=0 -p camera_type:=front"
```

## 5. Stop

```bash
make down
```
