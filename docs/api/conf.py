"""Sphinx configuration for RealGazebo API reference."""

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../../realgazebo-dora/ros2-bridge'))
sys.path.insert(0, os.path.abspath('../../src/jsbsim_bridge'))
sys.path.insert(0, os.path.abspath('../../src/image_viewer'))

project = 'RealGazebo API'
copyright = '2025, SUV-Lab'
author = 'SUV-Lab'
with open('../../.version') as f:
    version = f.read().strip() if os.path.exists('../../.version') else '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
html_theme = 'sphinx_rtd_theme'
html_static_path = []

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pydantic': ('https://docs.pydantic.dev/latest', None),
}

napoleon_google_docstring = True
autodoc_typehints = 'description'
autodoc_member_order = 'bysource'
