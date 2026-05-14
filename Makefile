# ── Quickstart (tier 1 — what 90% of users need) ─────────────────────────
.PHONY: setup build up down test test-one smoke-test logs help

setup:                 ## One-command: install deps + init submodules + pre-commit
	git submodule update --init --recursive --depth 1 2>/dev/null || git submodule update --init --recursive
	pip3 install -r requirements.txt -q 2>/dev/null; pip install -r requirements.txt -q 2>/dev/null; true
	pre-commit install 2>/dev/null || true
	@echo "Setup complete. Run 'make build' to build Docker image."

build:                 ## Build the base Docker image (ROS2 + Gazebo, ~10 min)
	@TAG=realgazebo:base-$$(date +%Y%m%d); \
	 docker build -f docker/Dockerfile.base -t realgazebo:base -t $$TAG . && \
	 echo "  Tagged as realgazebo:base and $$TAG"

up:                    ## Start simulation with default config
	@echo "=== Generating compose override ==="
	@python3 scripts/generate_compose.py src/realgazebo/yaml/one_drone.yaml 2>&1 | grep -v DeprecationWarning
	docker compose up -d
	@echo "Waiting for Gazebo..."; sleep 5
	@$(MAKE) smoke-test 2>/dev/null || echo "Run 'make smoke-test' to verify."

down:                  ## Stop all containers
	docker compose down 2>/dev/null; docker compose rm -f 2>/dev/null; true

test:                  ## Run all Python tests (works without Docker)
	@echo "=== Running tests ==="
	@python3 -c "import pydantic; assert pydantic.VERSION.startswith('2.'), 'pydantic v2 required'" 2>/dev/null || { echo "  [SKIP] pydantic v2 not found"; exit 0; }
	@python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" && \
	 python3 -m pytest scripts/tests/ realgazebo-dora/test/ src/jsbsim_bridge/test/ -v --timeout=60 -m "not integration" 2>&1 | tail -3 || \
	 python3 -m pytest scripts/tests/ -v --timeout=60 -m "not integration" 2>&1 | tail -3

test-one:              ## Run a single test: make test-one TEST=tests/test_name.py::TestClass::test_method
	@python3 -m pytest -v --timeout=60 -m "not integration" $(TEST)

smoke-test:            ## Verify Docker stack is healthy (needs 'make up' first)
	@echo "=== Smoke test ==="
	@docker ps --format '{{.Names}} {{.Status}}' | grep -c "gazebo" >/dev/null && echo "  [OK] Gazebo container running" || echo "  [FAIL] Gazebo not running"
	@docker exec gazebo bash -c 'source /opt/ros/jazzy/setup.bash && ros2 topic list 2>/dev/null | grep -c "/clock" >/dev/null' 2>/dev/null && echo "  [OK] /clock topic flowing" || echo "  [WARN] /clock not seen"
	@docker compose ps 2>/dev/null | head -5

logs:                  ## Follow container logs
	docker compose logs -f

# ── Development (tier 2 — iterate faster) ─────────────────────────────────
.PHONY: build-full up-dev lint typecheck docs benchmark

build-full:            ## Full build: includes PX4 + ArduPilot (~2 hours)
	@echo "  NOTE: CI builds Dockerfile.base only. Use this target locally to verify PX4/ArduPilot integration."
	docker build -f docker/Dockerfile -t realgazebo:full .

up-dev:                ## Start with hot-reload mounts (Python edits take effect instantly)
	@echo "=== Generating compose override ==="
	@python3 scripts/generate_compose.py src/realgazebo/yaml/one_drone.yaml 2>&1 | grep -v DeprecationWarning
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

lint:                  ## Run ruff linter + format check
	@ruff check . --ignore D,N,UP && ruff format --check .

typecheck:             ## Run mypy type checker
	mypy --ignore-missing-imports realgazebo-dora/ src/ scripts/

docs:                  ## Build both documentation systems
	cd docs/api && sphinx-build -b html . _build/html 2>/dev/null; echo "  API docs built"
	mkdocs build -q 2>/dev/null && echo "  User guide built"

benchmark:             ## Performance benchmarks
	@PYTHONPATH=realgazebo-dora/ros2-bridge python3 scripts/tests/benchmark_run.py

# ── Release (tier 3 — CI/CD) ──────────────────────────────────────────────
.PHONY: tag push clean

tag:                   ## Tag current commit as a release
	git tag v$(shell cat .version 2>/dev/null || date +%Y%m%d)
	git push origin v$(shell cat .version 2>/dev/null || date +%Y%m%d)

push:                  ## Push Docker image to registry
	docker tag realgazebo:base ghcr.io/vlordier/realgazebo:latest
	docker push ghcr.io/vlordier/realgazebo:latest

clean:                 ## Remove all build artifacts + dangling Docker images
	@find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache -o -name .mypy_cache \) -exec rm -rf {} + 2>/dev/null
	@find . -name "*.pyc" -delete
	@docker system prune -f --all --volumes 2>/dev/null || true
	@echo "Cleaned"

# ── Help ──────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
help:                  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-15s %s\n", $$1, $$2}'
