# RealGazebo Makefile — common development tasks
# Usage: make <target>

SHELL := /bin/bash
PYTHON := python3.12
DOCKER_COMPOSE := docker compose
VERSION := $(shell git describe --tags --always 2>/dev/null || echo "dev")

# ── Setup ────────────────────────────────────────────────────────────────────

.PHONY: setup install-deps pre-commit-install

setup: install-deps pre-commit-install
	@echo "Setup complete"

install-deps:
	pip install ruff pre-commit mypy pydantic hypothesis 2>/dev/null || true

pre-commit-install:
	@which pre-commit >/dev/null 2>&1 && pre-commit install || echo "pre-commit not found, skipping"

# ── Python ──────────────────────────────────────────────────────────────────

.PHONY: test test-v lint typecheck

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
	ruff check .
	ruff format --check .

typecheck:
	mypy --ignore-missing-imports realgazebo-dora/ src/ scripts/

# ── Docker Build ────────────────────────────────────────────────────────────

.PHONY: build-base build-full build-push

build-base:
	$(DOCKER_COMPOSE) build gazebo 2>&1 | tail -5

build-full:
	docker build -f docker/Dockerfile -t realgazebo:$(VERSION) . 2>&1 | tail -5

build-push:
	docker tag realgazebo:$(VERSION) ghcr.io/vlordier/realgazebo:$(VERSION)
	docker push ghcr.io/vlordier/realgazebo:$(VERSION)

# ── Simulation ──────────────────────────────────────────────────────────────

.PHONY: up up-dev down logs ps

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

ps:
	$(DOCKER_COMPOSE) ps

# ── Docs ─────────────────────────────────────────────────────────────────────

.PHONY: docs docs-serve

docs:
	cd docs && sphinx-build -b html . _build/html 2>/dev/null || echo "sphinx not installed"

docs-serve:
	cd docs/_build/html && python3 -m http.server 8080

# ── Benchmarks ───────────────────────────────────────────────────────────────

.PHONY: benchmark

benchmark:
	@echo "=== network_sim performance ==="
	@PYTHONPATH=realgazebo-dora/ros2-bridge $(PYTHON) -m scripts.tests.test_benchmark

# ── Version Management ──────────────────────────────────────────────────────

.PHONY: version bump-patch bump-minor tag

version:
	@echo "$(VERSION)"

bump-patch:
	@echo "Bumping patch version..."
	@echo $(VERSION) | awk -F. '{printf "%d.%d.%d\n", $$1, $$2, $$3+1}' > .version

bump-minor:
	@echo "Bumping minor version..."
	@echo $(VERSION) | awk -F. '{printf "%d.%d.0\n", $$1, $$2+1}' > .version

tag:
	git tag v$(shell cat .version 2>/dev/null || echo $(VERSION))
	git push origin v$(shell cat .version 2>/dev/null || echo $(VERSION))

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
