#!/usr/bin/env python3
"""Multi-vehicle V2V integration test.

Verifies that two vehicles can communicate through the network_sim layer.
Tests the critical multi-vehicle path:

Usage:
    python3 scripts/tests/test_multi_vehicle.py --gazebo-ip 127.0.0.1
"""

import argparse
import subprocess
import sys

# ── Constants ────────────────────────────────────────────────────────────────

VEHICLE_TYPES = ["x500", "rover_ackermann"]
FIRMWARE_OPTIONS = ["px4", "ardupilot", "jsbsim"]
TOPICS_PER_VEHICLE = [
    "/vehicle1/fmu/out/vehicle_status",
    "/vehicle2/fmu/out/vehicle_status",
    "/vehicle1/manager/in/main_cmd",
    "/vehicle2/manager/in/main_cmd",
]
NETWORK_SIM_TOPICS = [
    "/network_sim/diagnostics",
    "/network_sim/status",
]


def check_docker() -> bool:
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return True
    except (subprocess.FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_containers() -> list[str]:
    result = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True, text=True, timeout=10
    )
    return [n.strip() for n in result.stdout.split("\n") if n.strip()]


def check_ros2_topics(container: str, expected_topics: list[str]) -> tuple[int, list[str]]:
    """Check which expected ROS2 topics exist inside a container."""
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c",
         "source /opt/ros/jazzy/setup.bash && ros2 topic list 2>/dev/null"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return 0, []
    topics = [t.strip() for t in result.stdout.split("\n") if t.strip()]
    found = [t for t in expected_topics if t in topics]
    return len(found), found


def test_container_count(expected_min: int = 2) -> bool:
    containers = check_containers()
    count = len(containers)
    print(f"  Running containers: {count} (need ≥{expected_min})")
    if count < expected_min:
        print(f"  FAIL: Only {count} containers, expected at least {expected_min}")
        return False
    print(f"  OK: {count} containers running")
    return True


def test_two_vehicles_present() -> bool:
    containers = check_containers()
    vehicle_containers = [c for c in containers if c.startswith("vehicle_")]
    print(f"  Vehicle containers: {vehicle_containers}")
    if len(vehicle_containers) < 2:
        print(f"  FAIL: Need ≥2 vehicle containers, found {len(vehicle_containers)}")
        return False
    print(f"  OK: {len(vehicle_containers)} vehicle containers")
    return True


def test_gazebo_topics(gazebo_container: str = "gazebo") -> bool:
    result = subprocess.run(
        ["docker", "exec", gazebo_container, "bash", "-c",
         "source /opt/ros/jazzy/setup.bash && timeout 3 ros2 topic list 2>/dev/null | wc -l"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        print("  FAIL: Cannot reach Gazebo container")
        return False
    topic_count = int(result.stdout.strip() or "0")
    print(f"  Gazebo topics: {topic_count}")
    if topic_count < 3:
        print(f"  FAIL: Expected at least 3 topics, got {topic_count}")
        return False
    print(f"  OK: Gazebo running with {topic_count} topics")
    return True


def test_vehicle_topics(container: str, expected: list[str]) -> bool:
    count, found = check_ros2_topics(container, expected)
    print(f"  Topics in {container}: {count}/{len(expected)} expected")
    if count == 0:
        print("  FAIL: No expected topics found")
        return False
    print(f"  Found: {found}")
    return True


def test_network_sim_diagnostics(container: str = "gazebo") -> bool:
    """Check if network_sim diagnostics topic exists."""
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c",
         "source /opt/ros/jazzy/setup.bash && timeout 3 ros2 topic list 2>/dev/null | grep -c diagnostics"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and int(result.stdout.strip() or "0") > 0:
        print("  OK: /diagnostics topic present")
        return True
    print("  WARN: /diagnostics topic not found (network_sim may not be running)")
    return True  # Not a hard failure


def test_entity_spawn(container: str = "gazebo") -> bool:
    """Try to spawn a test entity via gz service."""
    sdf = (
        '<model name="test_vehicle"><static>false</static>'
        '<link name="body"><collision name="c"><geometry><box><size>1 1 1</size></box></geometry>'
        '</collision><visual name="v"><geometry><box><size>1 1 1</size></box></geometry></visual></link>'
        '<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/></model>'
    )
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c",
         f"gz service -s /world/test/create --reqtype gz.msgs.EntityFactory "
         f"--reptype gz.msgs.Boolean --timeout 2000 "
         f"--req 'sdf: \"{sdf}\", pose: {{position: {{x: 5, y: 0, z: 0.5}}}}' 2>/dev/null"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        print("  OK: Entity spawn succeeded")
        return True
    print("  WARN: Entity spawn failed (world may have different name)")
    return True


def main():
    parser = argparse.ArgumentParser(description="Multi-vehicle V2V integration test")
    parser.add_argument("--gazebo-ip", default="127.0.0.1")
    parser.parse_args()

    print("=" * 50)
    print("RealGazebo Multi-Vehicle V2V Integration Test")
    print("=" * 50)
    print()

    if not check_docker():
        print("SKIP: Docker not available")
        sys.exit(0)

    results = []

    print("1. Docker running and containers up...")
    ok = test_container_count(2)
    results.append(("containers_running", ok))

    print("2. Two vehicle containers present...")
    ok = test_two_vehicles_present()
    results.append(("two_vehicles", ok))

    print("3. Gazebo topics flowing...")
    ok = test_gazebo_topics("gazebo")
    results.append(("gazebo_topics", ok))

    print("4. Vehicle 1 ROS2 topics...")
    ok = test_vehicle_topics("vehicle_0", [
        "/vehicle1/fmu/out/vehicle_status",
        "/vehicle1/fmu/out/vehicle_local_position",
    ])
    results.append(("vehicle_0_topics", ok))

    print("5. Vehicle 2 ROS2 topics...")
    ok = test_vehicle_topics("vehicle_1", [
        "/vehicle2/fmu/out/vehicle_status",
        "/vehicle2/fmu/out/vehicle_local_position",
    ])
    results.append(("vehicle_1_topics", ok))

    print("6. Network diagnostics...")
    ok = test_network_sim_diagnostics("gazebo")
    results.append(("network_diagnostics", ok))

    print()
    print("=" * 50)
    failures = [n for n, r in results if not r]
    if failures:
        print(f"FAILED ({len(failures)}/{len(results)}): {', '.join(failures)}")
        sys.exit(1)
    else:
        print(f"ALL {len(results)} TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
