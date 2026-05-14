"""Shared test configuration: adds scripts/ to sys.path for all test files."""

import os
import sys

_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..')
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
