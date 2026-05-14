#!/bin/bash
# Smoke test for RealGazebo Docker stack.
# Returns 0 if healthy, 1 otherwise.
# Usage: bash scripts/smoke_test.sh

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
PASS=0
FAIL=0

pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }

# 1. Docker reachable
if docker ps >/dev/null 2>&1; then
    pass "Docker daemon reachable"
else
    fail "Docker daemon not reachable"
    exit 1
fi

# 2. Gazebo container running
if docker ps --format '{{.Names}}' | grep -q gazebo; then
    pass "Gazebo container running"
else
    fail "Gazebo container not running"
fi

# 3. Vehicle container running
if docker ps --format '{{.Names}}' | grep -q vehicle_; then
    VEHICLE_COUNT=$(docker ps --format '{{.Names}}' | grep -c vehicle_)
    pass "$VEHICLE_COUNT vehicle container(s) running"
else
    fail "No vehicle containers running"
fi

# 4. ROS2 topics flowing (Gazebo must be healthy)
TOPIC_COUNT=$(docker exec gazebo bash -c 'source /opt/ros/jazzy/setup.bash && timeout 5 ros2 topic list 2>/dev/null | wc -l' 2>/dev/null || echo "0")
if [ "$TOPIC_COUNT" -gt 0 ]; then
    pass "Gazebo publishing $TOPIC_COUNT ROS2 topics"
else
    fail "No ROS2 topics from Gazebo"
fi

# 5. /clock topic present
if docker exec gazebo bash -c 'source /opt/ros/jazzy/setup.bash && timeout 3 ros2 topic list 2>/dev/null' 2>/dev/null | grep -q "/clock"; then
    pass "/clock topic flowing"
else
    fail "/clock topic not found"
fi

# 6. Vehicle ROS2 topics present
if docker ps --format '{{.Names}}' | grep -q vehicle_; then
    VEHICLE_TOPICS=$(docker exec $(docker ps --format '{{.Names}}' | grep vehicle_ | head -1) bash -c 'source /opt/ros/jazzy/setup.bash && timeout 3 ros2 topic list 2>/dev/null | wc -l' 2>/dev/null || echo "0")
    if [ "$VEHICLE_TOPICS" -gt 0 ]; then
        pass "Vehicle publishing $VEHICLE_TOPICS ROS2 topics"
    else
        fail "No vehicle ROS2 topics"
    fi
fi

# Summary
echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
