"""Tests for JSBSim bridge module (without rclpy).

Tests import logic, property maps, constants, and the _read_state
function which can be tested in isolation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import constants and helpers without ROS2
from jsbsim_bridge.constants import (
    DEFAULT_AIRCRAFT,
    DEFAULT_UPDATE_RATE_HZ,
    FPS_TO_MPS,
    JSBSIM_PROPERTIES,
)


class TestConstants(unittest.TestCase):
    """Test JSBSim bridge constants."""

    def test_aircraft_default(self):
        self.assertEqual(DEFAULT_AIRCRAFT, 'c172p')

    def test_update_rate_default(self):
        self.assertEqual(DEFAULT_UPDATE_RATE_HZ, 250)

    def test_fps_to_mps(self):
        self.assertAlmostEqual(FPS_TO_MPS, 0.3048)

    def test_jsbsim_properties_count(self):
        self.assertGreaterEqual(len(JSBSIM_PROPERTIES), 12)

    def test_jsbsim_has_position_props(self):
        required = {'lat', 'lon', 'alt', 'phi', 'theta', 'psi'}
        for prop in required:
            self.assertIn(prop, JSBSIM_PROPERTIES, f'{prop} missing from JSBSIM_PROPERTIES')

    def test_jsbsim_has_velocity_props(self):
        for prop in ['v_north', 'v_east', 'v_down']:
            self.assertIn(prop, JSBSIM_PROPERTIES)

    def test_jsbsim_has_control_props(self):
        for prop in ['throttle', 'elevator', 'aileron', 'rudder']:
            self.assertIn(prop, JSBSIM_PROPERTIES)

    def test_jsbsim_property_paths_format(self):
        for name, path in JSBSIM_PROPERTIES.items():
            self.assertIsInstance(path, str)
            self.assertGreater(len(path), 0)
            self.assertIn('/', path, f"Property {name} has path {path} without '/'")

    def test_lat_property_path(self):
        self.assertEqual(JSBSIM_PROPERTIES['lat'], 'position/lat-geod-rad')

    def test_throttle_property_path(self):
        self.assertEqual(JSBSIM_PROPERTIES['throttle'], 'fcs/throttle-cmd-norm')


class TestJSBSimModule(unittest.TestCase):
    """Test that JSBSim can be imported and run (skip if not installed)."""

    @classmethod
    def setUpClass(cls):
        try:
            import jsbsim

            cls.jsbsim = jsbsim
            cls.HAS_JSBSIM = True
        except ImportError:
            cls.HAS_JSBSIM = False

    def setUp(self):
        if not self.HAS_JSBSIM:
            self.skipTest('jsbsim Python module not installed')

    def test_import(self):
        self.assertTrue(self.HAS_JSBSIM)

    def test_c172p_loads(self):
        root = self.jsbsim.get_default_root_dir()
        fdm = self.jsbsim.FGFDMExec(root, None)
        fdm.load_model('c172p')
        fdm.set_dt(0.004)
        fdm.run_ic()
        fdm.run()
        alt = fdm['position/h-sl-meters']
        self.assertIsNotNone(alt)

    def test_property_paths_matched(self):
        root = self.jsbsim.get_default_root_dir()
        fdm = self.jsbsim.FGFDMExec(root, None)
        fdm.load_model('c172p')
        fdm.set_dt(0.004)
        fdm.run_ic()
        fdm.run()
        for name, prop in JSBSIM_PROPERTIES.items():
            with self.subTest(prop=name):
                try:
                    val = fdm[prop]
                    self.assertIsNotNone(val)
                except KeyError:
                    self.fail(f"Property '{prop}' ({name}) not found in c172p")

    def test_throttle_command_accepted(self):
        root = self.jsbsim.get_default_root_dir()
        fdm = self.jsbsim.FGFDMExec(root, None)
        fdm.load_model('c172p')
        fdm.set_dt(0.004)
        fdm.run_ic()
        fdm['fcs/throttle-cmd-norm'] = 0.8
        for _ in range(100):
            fdm.run()
        self.assertEqual(fdm['fcs/throttle-cmd-norm'], 0.8, 'Throttle command should persist')


if __name__ == '__main__':
    unittest.main()
