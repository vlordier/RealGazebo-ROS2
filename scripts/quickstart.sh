#!/bin/bash
# RealGazebo Quickstart — one-command setup and run
# Usage: bash scripts/quickstart.sh [config_file]
#   config_file: Path to vehicle YAML (default: src/realgazebo/yaml/one_drone.yaml)
# What it does:
#   1. Checks prerequisites (Docker, git, Python)
#   2. Initializes submodules
#   3. Builds base Docker image (or pulls if available)
#   4. Starts the simulation
#   5. Runs smoke test
#   6. Shows next steps

set -euo pipefail

CONFIG_FILE="${1:-src/realgazebo/yaml/one_drone.yaml}"

CLEANUP() {
    docker compose down 2>/dev/null || true
}
trap CLEANUP EXIT

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo ""
echo -e "${BOLD}RealGazebo Quickstart${NC}"
echo "================================"
echo ""

# ── Step 1: Check prerequisites ──────────────────────────────────────────
info "Checking prerequisites..."

FAIL=0
command -v docker >/dev/null 2>&1 || { warn "docker not found"; FAIL=1; }
command -v git >/dev/null 2>&1 || { error "git not found"; FAIL=1; }
python3 -c "import yaml" 2>/dev/null || { warn "pyyaml not installed, installing..."; sudo apt-get install -y python3-yaml 2>/dev/null || pip3 install pyyaml --break-system-packages -q 2>/dev/null || true; }

if [ "$FAIL" = "1" ]; then
    error "Please install missing prerequisites and retry."
    exit 1
fi
info "All prerequisites met."

# ── Step 2: Initialize submodules ────────────────────────────────────────
info "Initializing submodules..."
git submodule update --init --recursive 2>&1 | tail -1
info "Submodules ready."

# ── Step 3: Check Docker image ───────────────────────────────────────────
info "Checking Docker image..."
if docker image inspect realgazebo:base >/dev/null 2>&1; then
    info "Base image 'realgazebo:base' found."
elif docker pull ghcr.io/vlordier/realgazebo:latest 2>/dev/null; then
    docker tag ghcr.io/vlordier/realgazebo:latest realgazebo:base
    info "Pulled pre-built image from registry."
else
    warn "No pre-built image found. Building from source (~10 min)..."
    docker build -f docker/Dockerfile.base -t realgazebo:base .
    info "Base image built."
fi

# ── Step 4: Start simulation ─────────────────────────────────────────────
info "Starting simulation with config: $CONFIG_FILE ..."
python3 scripts/generate_compose.py "$CONFIG_FILE" 2>&1 | grep -v DeprecationWarning || true
docker compose down 2>/dev/null || true
docker compose up -d 2>&1 | tail -3
info "Containers started. Waiting for Gazebo..."
sleep 8

# ── Step 5: Smoke test ──────────────────────────────────────────────────
info "Running smoke test..."
HEALTHY=0
if docker ps --format '{{.Names}}' | grep -q gazebo; then
    TOPIC_COUNT=$(docker exec gazebo bash -c 'source /opt/ros/jazzy/setup.bash && timeout 3 ros2 topic list 2>/dev/null | wc -l' 2>/dev/null || echo "0")
    if [ "$TOPIC_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}[OK]${NC} Gazebo running ($TOPIC_COUNT topics)"
        HEALTHY=1
    fi
fi

if [ "$HEALTHY" = "1" ]; then
    echo -e "${GREEN}✅ Simulation running successfully!${NC}"
else
    echo -e "${YELLOW}⚠️  Simulation started but not healthy yet.${NC}"
    echo "   Run 'make logs' to check status."
fi

# ── Step 6: Show next steps ──────────────────────────────────────────────
echo ""
echo -e "${BOLD}Next steps${NC}"
echo "  make test        # Run all Python tests"
echo "  make logs        # Follow simulation logs"
echo "  make ps          # List containers"
echo "  make down        # Stop simulation"
echo ""
echo -e "${BOLD}Send commands to vehicle${NC}"
echo '  docker exec gazebo bash -c "source /opt/ros/jazzy/setup.bash && ros2 topic pub /vehicle1/manager/in/main_cmd std_msgs/String \"data: ARM\""'
echo ""
info "Quickstart complete."
