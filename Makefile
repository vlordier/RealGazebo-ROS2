# ── Quickstart (tier 1 — what 90% of users need) ─────────────────────────
.PHONY: setup build up down ps test test-one test-docker coverage validate \
        fly-ardupilot arm takeoff land smoke-test logs logs-v help

# Python runner with scripts/ on the import path (no sys.path hacks needed)
_PYTHON = PYTHONPATH=scripts uv run python3

# Default vehicle index for arm/takeoff/land (0 = vehicle_0 → /vehicle1/mavros)
VEHICLE ?= 0

setup:                 ## Install deps + init submodules + pre-commit
	git submodule update --init --recursive --depth 1 2>/dev/null || git submodule update --init --recursive
	uv venv 2>/dev/null; uv pip install -r requirements.txt -q 2>/dev/null || true
	pre-commit install 2>/dev/null || true
	@echo "Setup complete."

build:                 ## Build base Docker image (ROS2 + Gazebo, ~10 min)
	@TAG=realgazebo:base-$$(date +%Y%m%d); \
	 docker build -f docker/Dockerfile.base -t realgazebo:base -t $$TAG . && \
	 echo "  Tagged realgazebo:base and $$TAG"

up:                    ## Start simulation with default config
	@echo "=== Generating compose ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/one_drone.yaml 2>&1 | grep -v DeprecationWarning
	docker compose up -d
	@echo "Waiting for Gazebo..."; sleep 5
	@$(MAKE) smoke-test 2>/dev/null || echo "Run 'make smoke-test' to verify."

down:                  ## Stop all containers
	docker compose down 2>/dev/null; docker compose rm -f 2>/dev/null; true

ps:                    ## List running containers
	docker compose ps 2>/dev/null

test:                  ## Run all Python tests (works without Docker)
	@echo "=== Tests ==="
	@$(_PYTHON) -m pytest scripts/tests/ -v -m "not integration" --tb=line 2>&1 | tail -1

test-one:              ## Run a single test: TEST=tests/test_name.py::TestClass::test_method
	@$(_PYTHON) -m pytest -v -m "not integration" $(TEST)

test-docker:           ## Run tests inside a Docker container
	@echo "=== Building test image ==="
	@docker build -f docker/Dockerfile.test -t realgazebo:test . 2>&1 | tail -3
	@echo "=== Running tests ==="
	@docker run --rm realgazebo:test 2>&1 | tail -1

coverage:              ## Run tests with coverage report
	@echo "=== Coverage ==="
	@$(_PYTHON) -m pytest scripts/tests/ -m "not integration" --cov=scripts --cov-report=term --cov-report=html 2>&1 | tail -5
	@echo "  HTML: htmlcov/index.html"

validate:              ## Quick pipeline check: YAML → compose (no Docker)
	@echo "=== Validating example.yaml ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/example.yaml --validate
	@echo "=== Validating one_drone.yaml ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/one_drone.yaml --validate
	@echo "=== Validating ardupilot_demo.yaml ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/ardupilot_demo.yaml --validate

# ── ArduPilot flight targets ────────────────────────────────────────────

build-full:            ## Full build: includes PX4 + ArduPilot (~2 hours)
	@echo "  NOTE: CI builds base only. Use this for local ArduPilot testing."
	docker build -f docker/Dockerfile -t realgazebo:full \
	  --cache-from realgazebo:full \
	  --build-arg BUILDKIT_INLINE_CACHE=1 .

fly-ardupilot:         ## One-shot: build-full + up + arm + takeoff
	@echo "=== Step 1: Build full image (if needed) ==="
	@docker image inspect realgazebo:full >/dev/null 2>&1 || make build-full
	@echo "=== Step 2: Start simulation ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/ardupilot_demo.yaml --image realgazebo:full 2>&1 | grep -v DeprecationWarning
	@docker compose down 2>/dev/null || true
	@docker compose up -d 2>&1 | tail -1
	@echo "  Waiting for Gazebo + vehicle..."
	@for i in $$(seq 1 30); do \
	  if docker ps --format '{{.Names}}' | grep -q vehicle_0; then \
	    echo "  Ready after $$((i * 3))s"; break; fi; sleep 3; done
	@echo "=== Step 3: Arm ==="
	@sleep 5; $(MAKE) arm VEHICLE=0 2>/dev/null
	@sleep 3
	@echo "=== Step 4: Takeoff to 10m ==="
	@$(MAKE) takeoff VEHICLE=0 2>/dev/null
	@echo "  Drone should be airborne!"
	@echo "  make land       # Land"
	@echo "  make logs-v     # Watch vehicle logs"
	@echo "  make ps         # Check status"
	@echo ""
	@echo "  To see the drone in Gazebo:"
	@echo "    export HEADLESS=false; make down && make up"
	@echo "  Or on macOS with XQuartz:"
	@echo "    xhost +localhost; HEADLESS=false make fly-ardupilot"
	@echo "  For UE5: run RealGazeboUE5 project, listens on port 5005"

arm:                   ## Arm vehicle via MAVROS (VEHICLE=0). Needs ArduPilot running.
	$(eval _MAV = $(shell expr $(VEHICLE) + 1))
	@docker exec vehicle_$(VEHICLE) bash -c '\
	 source /opt/ros/jazzy/setup.bash && source /home/user/realgazebo/RealGazebo-ROS2/install/setup.bash && \
	 ros2 service call /vehicle$(_MAV)/mavros/cmd/arming \
	   mavros_msgs/srv/CommandBool "{value: true}"' 2>/dev/null || \
	 echo "  [FAIL] vehicle_$(VEHICLE) not reachable (ArduPilot running?)"

takeoff:               ## Take off to 10m (VEHICLE=0). Needs armed.
	$(eval _MAV = $(shell expr $(VEHICLE) + 1))
	@docker exec vehicle_$(VEHICLE) bash -c '\
	 source /opt/ros/jazzy/setup.bash && source /home/user/realgazebo/RealGazebo-ROS2/install/setup.bash && \
	 ros2 service call /vehicle$(_MAV)/mavros/cmd/takeoff \
	   mavros_msgs/srv/CommandTOL \
	   "{min_pitch: 0.0, yaw: 0.0, latitude: 0.0, longitude: 0.0, altitude: 10.0}"' \
	 2>/dev/null || echo "  [FAIL] Takeoff failed"

land:                  ## Land vehicle (VEHICLE=0). Needs flying.
	$(eval _MAV = $(shell expr $(VEHICLE) + 1))
	@docker exec vehicle_$(VEHICLE) bash -c '\
	 source /opt/ros/jazzy/setup.bash && source /home/user/realgazebo/RealGazebo-ROS2/install/setup.bash && \
	 ros2 service call /vehicle$(_MAV)/mavros/cmd/land \
	   mavros_msgs/srv/CommandTOL \
	   "{min_pitch: 0.0, yaw: 0.0, latitude: 0.0, longitude: 0.0, altitude: 0.0}"' \
	 2>/dev/null || echo "  [FAIL] Land failed"

smoke-test:            ## Verify Docker stack is healthy (needs 'make up')
	@echo "=== Smoke test ==="
	@docker ps --format '{{.Names}} {{.Status}}' | grep -c "gazebo" >/dev/null && echo "  [OK] Gazebo running" || echo "  [FAIL] Gazebo not running"
	@docker exec gazebo bash -c 'source /opt/ros/jazzy/setup.bash && ros2 topic list 2>/dev/null | grep -c "/clock" >/dev/null' 2>/dev/null && echo "  [OK] /clock flowing" || echo "  [WARN] /clock not seen"
	@docker compose ps 2>/dev/null | head -5

logs:                  ## Follow all container logs
	docker compose logs -f

logs-v:                ## Follow logs for a specific vehicle: make logs-v VEHICLE=2
	docker compose logs -f vehicle_$(VEHICLE)

# ── Development (tier 2) ────────────────────────────────────────────────────
.PHONY: build-full up-dev format lint typecheck docs benchmark

up-dev:                ## Start with hot-reload mounts
	@echo "=== Generating compose ==="
	@$(_PYTHON) scripts/generate_compose.py src/realgazebo/yaml/one_drone.yaml 2>&1 | grep -v DeprecationWarning
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

lint:                  ## Run ruff linter + format check
	@uv run ruff check . --ignore D,N,UP && uv run ruff format --check .

format:                ## Auto-format all Python files
	@uv run ruff format . && echo "Formatted."

typecheck:             ## Run mypy + pyright
	@echo "=== mypy ==="; uv run mypy --ignore-missing-imports scripts/ 2>&1 | tail -2
	@echo "=== pyright ==="; uv run pyright scripts/generate_compose.py scripts/tests/ 2>&1 | tail -2

docs:                  ## Build documentation
	cd docs/api && sphinx-build -b html . _build/html 2>/dev/null; echo "  API docs built"
	mkdocs build -q 2>/dev/null && echo "  User guide built"

benchmark:             ## Performance benchmarks
	@PYTHONPATH="scripts:realgazebo-dora/ros2-bridge" uv run python3 scripts/tests/benchmark_run.py

# ── Release (tier 3) ─────────────────────────────────────────────────────────
.PHONY: tag push clean

tag:                   ## Tag current commit
	git tag v$(shell cat .version 2>/dev/null || date +%Y%m%d)
	git push origin v$(shell cat .version 2>/dev/null || date +%Y%m%d)

push:                  ## Push Docker image to registry
	docker tag realgazebo:base ghcr.io/vlordier/realgazebo:latest
	docker push ghcr.io/vlordier/realgazebo:latest

clean:                 ## Remove build artifacts + dangling Docker images
	@find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) -exec rm -rf {} + 2>/dev/null
	@find . -name "*.pyc" -delete
	@docker system prune -f --all --volumes 2>/dev/null || true
	@echo "Cleaned"

# ── Help ─────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
help:                  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-15s %s\n", $$1, $$2}'
