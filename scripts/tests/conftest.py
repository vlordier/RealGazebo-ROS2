"""Shared test fixtures and configuration for all test files.

Fixtures:
    example_config  -- Loaded YAML config from example.yaml (cached per session)
    compose_override -- Generated docker-compose dict from example.yaml (cached)
    render_sdf      -- Callable that renders a Jinja SDF template to XML string
    models_dir      -- Path to the Gazebo SDF model templates directory
"""

import os
from functools import cache

import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
MODELS_DIR = os.path.join(PROJECT_DIR, 'src', 'realgazebo', 'models')
EXAMPLE_YAML = os.path.join(PROJECT_DIR, 'src', 'realgazebo', 'yaml', 'example.yaml')


# ── Session-scoped fixtures (loaded once, shared across all tests) ──────


@cache
def _load_config():
    from generate_compose import load_config

    return load_config(EXAMPLE_YAML)


@cache
def _compose_override():
    from generate_compose import generate_compose_override

    return generate_compose_override(_load_config())


@cache
def _sdf_env():
    from jinja2 import Environment, FileSystemLoader

    return Environment(loader=FileSystemLoader(MODELS_DIR))


@pytest.fixture(scope='session')
def example_config():
    """Fixture: cached YAML config from example.yaml (all 10 vehicles)."""
    return _load_config()


@pytest.fixture(scope='session')
def compose_override():
    """Fixture: cached docker-compose override dict from example.yaml."""
    return _compose_override()


@pytest.fixture(scope='session')
def models_dir():
    """Fixture: path to SDF model templates directory."""
    return MODELS_DIR


@pytest.fixture(scope='session')
def render_sdf():
    """Fixture: callable that renders an SDF template to an XML string.

    Usage in tests:
        def test_foo(self, render_sdf):
            output = render_sdf('x500.sdf.jinja', firmware='px4')
    """

    def _render(template_name, firmware='px4'):
        env = _sdf_env()
        template = env.get_template(template_name)
        return template.render(unreal_ip='127.0.0.1', unreal_port='5005', firmware=firmware)

    return _render
