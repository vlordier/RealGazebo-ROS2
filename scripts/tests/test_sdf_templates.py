"""Validate all SDF Jinja templates render to well-formed XML with correct plugins."""

import xml.etree.ElementTree as ET


class TestSdfTemplateValidation:
    """Renders every template at every firmware variant and validates XML + plugin selection.

    Uses the `render_sdf` fixture from conftest.py (session-scoped, cached).
    """

    def _check(
        self, render_sdf, template_name, firmware='px4', expect_plugin=None, absent_plugin=None
    ):
        output = render_sdf(template_name, firmware=firmware)
        root = ET.fromstring(output)
        assert root is not None
        assert root.tag == 'sdf'
        if expect_plugin:
            assert expect_plugin in output, f'{template_name} fw={firmware} missing {expect_plugin}'
        if absent_plugin:
            assert absent_plugin not in output, (
                f'{template_name} fw={firmware} should NOT have {absent_plugin}'
            )
        return output

    def test_x500_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'x500.sdf.jinja')

    def test_x500_lidar_2d_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'x500_lidar_2d.sdf.jinja')

    def test_rover_ackermann_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'rover_ackermann.sdf.jinja')

    def test_boat_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'boat.sdf.jinja')

    def test_lc_62_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'lc_62.sdf.jinja')

    def test_rock_renders_valid_xml(self, render_sdf):
        self._check(render_sdf, 'rock/rock.sdf.jinja')

    def test_x500_ardupilot_has_gz_ardupilot_no_px4(self, render_sdf):
        self._check(
            render_sdf,
            'x500.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-multicopter-motor-model-system',
        )

    def test_rover_ardupilot_has_gz_ardupilot_no_px4(self, render_sdf):
        self._check(
            render_sdf,
            'rover_ackermann.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-joint-controller-system',
        )

    def test_boat_ardupilot_has_gz_ardupilot_no_px4(self, render_sdf):
        self._check(
            render_sdf,
            'boat.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='gz-sim-multicopter-motor-model-system',
        )

    def test_lc_62_ardupilot_has_gz_ardupilot(self, render_sdf):
        self._check(
            render_sdf,
            'lc_62.sdf.jinja',
            firmware='ardupilot',
            expect_plugin='gz-ardupilot',
            absent_plugin='MotorFailureROS2',
        )

    def test_x500_px4_has_motor_plugins_no_ardupilot(self, render_sdf):
        self._check(
            render_sdf,
            'x500.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-multicopter-motor-model-system',
            absent_plugin='gz-ardupilot',
        )

    def test_rover_px4_has_joint_controllers_no_ardupilot(self, render_sdf):
        self._check(
            render_sdf,
            'rover_ackermann.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-joint-controller-system',
            absent_plugin='gz-ardupilot',
        )

    def test_boat_px4_has_motor_plugins_no_ardupilot(self, render_sdf):
        self._check(
            render_sdf,
            'boat.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-multicopter-motor-model-system',
            absent_plugin='gz-ardupilot',
        )

    def test_lc_62_px4_has_failure_plugins(self, render_sdf):
        output = self._check(
            render_sdf,
            'lc_62.sdf.jinja',
            firmware='px4',
            expect_plugin='MotorFailureROS2',
            absent_plugin='gz-ardupilot',
        )
        assert 'ServoFailureROS2' in output, 'lc_62 PX4 missing ServoFailureROS2'

    def test_x500_jsbsim_fallthrough(self, render_sdf):
        self._check(render_sdf, 'x500.sdf.jinja', firmware='jsbsim')

    def test_rover_jsbsim_fallthrough(self, render_sdf):
        self._check(render_sdf, 'rover_ackermann.sdf.jinja', firmware='jsbsim')

    def test_boat_jsbsim_fallthrough(self, render_sdf):
        self._check(render_sdf, 'boat.sdf.jinja', firmware='jsbsim')

    def test_joint_names_match_px4_x500_base(self, render_sdf):
        output = self._check(
            render_sdf,
            'x500.sdf.jinja',
            firmware='px4',
            expect_plugin='gz-sim-multicopter-motor-model-system',
        )
        for joint in ['rotor_0_joint', 'rotor_1_joint', 'rotor_2_joint', 'rotor_3_joint']:
            assert f'<jointName>{joint}</jointName>' in output, f'Missing PX4 joint: {joint}'

    def test_joint_names_match_px4_rover(self, render_sdf):
        output = self._check(
            render_sdf,
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
            assert f'<joint_name>{joint}</joint_name>' in output, f'Missing PX4 joint: {joint}'

    def test_all_templates_all_firmwares(self, render_sdf):
        """Combinatorial smoke: every template at every firmware produces valid XML."""
        templates = [
            'x500.sdf.jinja',
            'x500_lidar_2d.sdf.jinja',
            'rover_ackermann.sdf.jinja',
            'boat.sdf.jinja',
            'lc_62.sdf.jinja',
            'rock/rock.sdf.jinja',
        ]
        for t in templates:
            for fw in ['px4', 'ardupilot', 'jsbsim']:
                output = render_sdf(t, firmware=fw)
                ET.fromstring(output)
