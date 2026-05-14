# RealGazebo Makefile — common development tasks
# Usage: make <target>
#   make test          Run all Python tests
#   make test-v        Run all Python tests (verbose)
#   make lint          Run flake8 on Python code
#   make build-base    Build ARM64 base Docker image (ROS2 + Gazebo only)
#   make build-full    Build ARM64 full Docker image (includes PX4 + ArduPilot)
#   make up            Start simulation with Docker Compose
#   make up-dev        Start simulation with hot-reload mounts
#   make down          Stop simulation
#   make logs          Follow all logs
#   make clean         Remove build artifacts
#   make shellcheck    Check bash scripts

SHELL := /bin/bash
PYTHON := python3.12
DOCKER_COMPOSE := docker compose

# ── Python ──────────────────────────────────────────────────────────────────

.PHONY: test test-v lint

test:
	@echo "=== Running all Python tests ==="
	@$(PYTHON) -m unittest discover -s src/manager/test -v -t . 2>&1 | tail -1
	@$(PYTHON) -m unittest discover -s src/drone_controller/test -v -t . 2>&1 | tail -1
	@$(PYTHON) -m unittest discover -s scripts/tests -v 2>&1 | tail -1
	@$(PYTHON) -m unittest discover -s realgazebo-dora/test -v 2>&1 | tail -1

test-v:
	$(PYTHON) -m unittest discover -s src/manager/test -v -t .
	$(PYTHON) -m unittest discover -s src/drone_controller/test -v -t .
	$(PYTHON) -m unittest discover -s scripts/tests -v
	$(PYTHON) -m unittest discover -s realgazebo-dora/test -v

lint:
	@echo "=== Flake8 ==="
	@find src/manager src/drone_controller src/image_viewer scripts -name "*.py" -not -path "*/px4_msgs/*" -exec flake8 {} \; 2>/dev/null || echo "  (flake8 not installed, skipping)"

# ── Docker Build ────────────────────────────────────────────────────────────

.PHONY: build-base build-full

build-base:
	$(DOCKER_COMPOSE) build gazebo 2>&1 | tail -5

build-full:
	docker build -f docker/Dockerfile -t realgazebo:arm64 . 2>&1 | tail -5

# ── Simulation ──────────────────────────────────────────────────────────────

.PHONY: up up-dev down logs

up:
	@echo "Generating compose override..."
	@$(PYTHON) scripts/generate_compose.py src/realgazebo/yaml/example.yaml 2>&1
	$(DOCKER_COMPOSE) up -d

up-dev:
	@echo "Starting dev mode (source mounted for hot-reload)..."
	@$(PYTHON) scripts/generate_compose.py src/realgazebo/yaml/example.yaml 2>&1
	$(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

# ── Maintenance ─────────────────────────────────────────────────────────────

.PHONY: clean shellcheck

clean:
	@echo "Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@echo "Done"

shellcheck:
	shellcheck scripts/*.sh
