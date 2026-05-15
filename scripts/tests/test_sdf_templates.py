"""Validate all SDF Jinja templates render to well-formed XML with correct plugins."""

import os
import unittest
import xml.etree.ElementTree as ET

from jinja2 import Environment, FileSystemLoader

MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'realgazebo', 'models')
_env = Environment(loader=FileSystemLoader(MODELS_DIR))


def render_sdf(template_name, firmware='px4'):
    return _env.get_template(template_name).render(
        unreal_ip='127.0.0.1', unreal_port='5005', firmware=firmware
    )


class TestSdfTemplateValidation(unittest.TestCase):
    def _check(self, template_name, firmware='px4', expect_plugin=None, absent_plugin=None):
        output = render_sdf(template_name, firmware=firmware)
        root = ET.fromstring(output)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, 'sdf')
        if expect_plugin:
            self.assertIn(
                expect_plugin, output, f'{template_name} fw={firmware} missing {expect_plugin}'
            )
        if absent_plugin:
            self.assertNotIn(
                absent_plugin,
                output,
                f'{template_name} fw={firmware} should NOT have {absent_plugin}',
            )
        return output

    def test_x500_renders_valid_xml(self):
        self._check('x500.sdf.jinja')

    def test_x500_lidar_2d_renders_valid_xml(self):
        self._check('x500_lidar_2d.sdf.jinja')

    def test_rover_ackermann_renders_valid_xml(self):
        self._check('rover_ackermann.sdf.jinja')

    def test_boat_renders_valid_xml(self):
        self._check('boat.sdf.jinja')

    def test_lc_62_renders_valid_xml(self):
        self._check('lc_62.sdf.jinja')

    def test_rock_renders_valid_xml(self):
        self._check('rock/rock.sdf.jinja')

    def test_x500_ardupilot_has_gz_ardupilot_no_px4(self):
        self._check(
            'x500.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-multicopter-motor-model-system',
        )

    def test_rover_ardupilot_has_gz_ardupilot_no_px4(self):
        self._check(
            'rover_ackermann.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-joint-controller-system',
        )

    def test_boat_ardupilot_has_gz_ardupilot_no_px4(self):
        self._check(
            'boat.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-multicopter-motor-model-system',
        )

    def test_lc_62_ardupilot_has_gz_ardupilot(self):
        self._check(
            'lc_62.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='MotorFailureROS2',
        )

    def test_x500_px4_has_motor_plugins_no_ardupilot(self):
        self._check(
            'x500.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-multicopter-motor-model-system',
            absent_plugin='gz-ardupilot',
        )

    def test_rover_px4_has_joint_controllers_no_ardupilot(self):
        self._check(
            'rover_ackermann.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-joint-controller-system',
            absent_plugin='gz-ardupilot',
        )

    def test_boat_px4_has_motor_plugins_no_ardupilot(self):
        self._check(
            'boat.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-multicopter-motor-model-system',
            absent_plugin='gz-ardupilot',
        )

    def test_lc_62_px4_has_failure_plugins(self):
        output = self._check(
            'lc_62.sdf.jinja',
            firmware='px4',
            expect_plugin='MotorFailureROS2',
            absent_plugin='gz-ardupilot',
        )
        self.assertIn('ServoFailureROS2', output, 'lc_62 PX4 missing ServoFailureROS2')

    def test_x500_jsbsim_fallthrough(self):
        self._check('x500.sdf.jinja', firmware='jsbsim')

    def test_rover_jsbsim_fallthrough(self):
        self._check('rover_ackermann.sdf.jinja', firmware='jsbsim')

    def test_boat_jsbsim_fallthrough(self):
        self._check('boat.sdf.jinja', firmware='jsbsim')

    def test_joint_names_match_px4_x500_base(self):
        output = self._check(
            'x500.sdf.jinja', firmware='px4', expect_plugin='gz-sim-multicopter-motor-model-system'
        )
        for joint in ['rotor_0_joint', 'rotor_1_joint', 'rotor_2_joint', 'rotor_3_joint']:
            self.assertIn(f'<jointName>{joint}</jointName>', output, f'Missing PX4 joint: {joint}')

    def test_joint_names_match_px4_rover(self):
        output = self._check(
            'rover_ackermann.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-joint-controller-system',
        )
        for joint in [
            'rover_ackermann/FrontLeftWheelJoint',
            'rover_ackermann/FrontRightWheelJoint',
            'rover_ackermann/RearRightWheelJoint',
            'rover_ackermann/RearLeftWheelJoint',
        ]:
            self.assertIn(
                f'<joint_name>{joint}</joint_name>', output, f'Missing PX4 joint: {joint}'
            )

    def test_render_all_firmwares_all_templates(self):
        """Smoke test: every template at every firmware produces valid XML."""
        templates = [
            'x500.sdf.jinja',
            'x500_lidar_2d.sdf.jinja',
            'rover_ackermann.sdf.jinja',
            'boat.sdf.jinja',
            'lc_62.sdf.jinja',
            'rock/rock.sdf.jinja',
        ]
        firmwares = ['px4', 'ardupilot', 'jsbsim']
        for t in templates:
            for fw in firmwares:
                output = render_sdf(t, firmware=fw)
                ET.fromstring(output)  # raises on malformed XML
