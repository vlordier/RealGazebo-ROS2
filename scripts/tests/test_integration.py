"""Integration tests requiring Docker + running stack.
Run with: python -m pytest scripts/tests/test_integration.py -m integration
"""

import subprocess
import unittest

import pytest


class TestMultiVehicleIntegration(unittest.TestCase):
    @pytest.mark.integration
    def test_docker_reachable(self):
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, 'Docker daemon not reachable')

    @pytest.mark.integration
    def test_gazebo_container_running(self):
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        self.assertTrue(any('gazebo' in n for n in names), f'No gazebo container. Found: {names}')

    @pytest.mark.integration
    def test_vehicle_containers_running(self):
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True
        )
        names = [n for n in result.stdout.strip().split('\n') if n]
        self.assertGreater(
            sum(1 for n in names if 'vehicle_' in n), 0, f'No vehicle containers. Found: {names}'
        )
