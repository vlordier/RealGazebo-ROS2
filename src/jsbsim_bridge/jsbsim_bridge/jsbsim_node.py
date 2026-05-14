#!/usr/bin/env python3
"""JSBSim Flight Dynamics Model bridge for RealGazebo.

Loads a JSBSim aircraft model, steps the simulation locked to Gazebo's /clock,
and publishes aircraft state as ROS2 topics. Subscribes to actuator
commands for flight control surface inputs.

Multi-aircraft: each instance uses a unique namespace (/jsbsim_{instance_id}/...).
Clock sync: listens to /clock and steps JSBSim in sim-time chunks.

Usage:
    ros2 launch jsbsim_bridge jsbsim.launch.py instance_id:=0 aircraft:=c172p
"""

import math
import threading

import rclpy
from geometry_msgs.msg import PoseStamped, TwistStamped
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
from std_msgs.msg import Float64MultiArray, Header, String

from jsbsim_bridge.constants import (
    CONTROL_PROPERTIES,
    DEFAULT_AIRCRAFT,
    DEFAULT_FRAME_ID,
    DEFAULT_UPDATE_RATE_HZ,
    FPS_TO_MPS,
    JSBSIM_PROPERTIES,
)


class JSBSimBridge(Node):
    """Bridges JSBSim FDM to ROS2 topics, locked to simulation clock."""

    def __init__(self):
        instance_id = self._declare_param("instance_id", 0)
        aircraft = self._declare_param("aircraft", DEFAULT_AIRCRAFT)
        update_rate = self._declare_param("update_rate", DEFAULT_UPDATE_RATE_HZ)
        frame_id = self._declare_param("frame_id", DEFAULT_FRAME_ID)

        ns = f"jsbsim_{instance_id}" if instance_id else "jsbsim"
        super().__init__(ns)
        self._ns = ns
        self._instance_id = instance_id
        self._dt = 1.0 / update_rate
        self._frame_id = frame_id

        # Initialize JSBSim
        self._fdm = self._init_jsbsim(aircraft)
        if self._fdm is None:
            raise RuntimeError(f"Failed to load JSBSim aircraft: {aircraft}")

        # Simulation time tracking (locked to /clock)
        self._last_clock: float | None = None
        self._sim_lag: float = 0.0

        # Publishers
        topic_prefix = f"/{ns}"
        self._pose_pub = self.create_publisher(PoseStamped, f"{topic_prefix}/pose", 10)
        self._velocity_pub = self.create_publisher(TwistStamped, f"{topic_prefix}/velocity", 10)
        self._pose_cov_pub = self.create_publisher(PoseStamped, f"{topic_prefix}/pose_ground_truth", 10)
        self._status_pub = self.create_publisher(String, f"{topic_prefix}/status", 10)

        # Clock subscriber (Gazebo sync)
        self.create_subscription(Clock, "/clock", self._clock_callback, 10)

        # Control subscriber
        self._latest_controls = [0.0, 0.0, 0.0, 0.0]
        self._controls_lock = threading.Lock()
        self.create_subscription(
            Float64MultiArray, f"{topic_prefix}/controls",
            self._control_callback, 10
        )

        # Timer-driven simulation step (best-effort, clock callback does the real work)
        self.create_timer(self._dt, self._step_if_clock_elapsed)

        self.get_logger().info(
            f"[jsbsim:{instance_id}] Loaded {aircraft} @ {update_rate}Hz,"
            f" topics under /{ns}/"
        )

    # ── Parameter helpers ───────────────────────────────────────────────

    def _declare_param(self, name: str, default):
        self.declare_parameter(name, default)
        return self.get_parameter(name).value

    # ── JSBSim init ─────────────────────────────────────────────────────

    def _init_jsbsim(self, aircraft: str):
        try:
            import jsbsim
            root = jsbsim.get_default_root_dir()
            fdm = jsbsim.FGFDMExec(root, None)
            fdm.load_model(aircraft)
            fdm.set_dt(self._dt)
            fdm.run_ic()
            for _ in range(10):
                fdm.run()
            self.get_logger().info(f"[jsbsim] Aircraft {aircraft} initialized")
            return fdm
        except Exception as e:
            self.get_logger().error(f"[jsbsim] Init failed: {e}")
            return None

    # ── Clock sync ──────────────────────────────────────────────────────

    def _clock_callback(self, msg: Clock):
        t = msg.clock.sec + msg.clock.nanosec / 1e9
        if self._last_clock is not None:
            elapsed = t - self._last_clock
            if elapsed > 0:
                self._sim_lag += elapsed
        self._last_clock = t

    def _step_if_clock_elapsed(self):
        """Step JSBSim to catch up with simulation clock."""
        steps = 0
        max_steps = int(1.0 / self._dt)  # Safety: at most 1 sim-second per tick
        while self._sim_lag >= self._dt and steps < max_steps:
            self._step()
            self._sim_lag -= self._dt
            steps += 1
        if steps:
            self.get_logger().debug(f"[jsbsim] Stepped {steps}x ({self._sim_lag:.4f}s remaining)")

    # ── Control input ───────────────────────────────────────────────────

    def _control_callback(self, msg: Float64MultiArray):
        with self._controls_lock:
            for i in range(min(len(msg.data), 4)):
                self._latest_controls[i] = msg.data[i]

    # ── Simulation step ─────────────────────────────────────────────────

    def _step(self):
        fdm = self._fdm
        if fdm is None:
            return

        # Apply control inputs
        with self._controls_lock:
            for prop, val in zip(CONTROL_PROPERTIES, self._latest_controls):
                jsb_prop = JSBSIM_PROPERTIES[prop]
                try:
                    fdm[jsb_prop] = val
                except KeyError:
                    pass

        fdm.run()

        # Read state (in one batch)
        state = self._read_state(fdm)
        if state is None:
            return

        self._publish_state(state)

    def _read_state(self, fdm):
        """Read JSBSim state properties into a dict, returns None on failure."""
        try:
            lat = fdm[JSBSIM_PROPERTIES["lat"]]
            lon = fdm[JSBSIM_PROPERTIES["lon"]]
            alt = fdm[JSBSIM_PROPERTIES["alt"]]
            phi = fdm[JSBSIM_PROPERTIES["phi"]]
            theta = fdm[JSBSIM_PROPERTIES["theta"]]
            psi = fdm[JSBSIM_PROPERTIES["psi"]]
            vn = fdm[JSBSIM_PROPERTIES["v_north"]] * FPS_TO_MPS
            ve = fdm[JSBSIM_PROPERTIES["v_east"]] * FPS_TO_MPS
            vd = fdm[JSBSIM_PROPERTIES["v_down"]] * FPS_TO_MPS
        except KeyError as e:
            self.get_logger().warn(f"[jsbsim] Property missing: {e}")
            return None

        # Euler → quaternion
        cy = math.cos(psi * 0.5)
        sy = math.sin(psi * 0.5)
        cp = math.cos(theta * 0.5)
        sp = math.sin(theta * 0.5)
        cr = math.cos(phi * 0.5)
        sr = math.sin(phi * 0.5)

        return {
            "lat": lat * 180.0 / math.pi,
            "lon": lon * 180.0 / math.pi,
            "alt": alt,
            "qx": sr * cp * cy - cr * sp * sy,
            "qy": cr * sp * cy + sr * cp * sy,
            "qz": cr * cp * sy - sr * sp * cy,
            "qw": cr * cp * cy + sr * sp * sy,
            "vx": vn, "vy": ve, "vz": vd,
            "vwx": 0.0, "vwy": 0.0, "vwz": 0.0,  # angular rates not available in c172p
        }

    def _publish_state(self, state: dict):
        stamp = self.get_clock().now().to_msg()
        hdr = Header(stamp=stamp, frame_id=self._frame_id)

        # Pose
        pose = PoseStamped(header=hdr)
        pose.pose.position.x = state["lon"]
        pose.pose.position.y = state["lat"]
        pose.pose.position.z = state["alt"]
        pose.pose.orientation.x = state["qx"]
        pose.pose.orientation.y = state["qy"]
        pose.pose.orientation.z = state["qz"]
        pose.pose.orientation.w = state["qw"]
        self._pose_pub.publish(pose)

        # Velocity
        vel = TwistStamped(header=hdr)
        vel.twist.linear.x = state["vx"]
        vel.twist.linear.y = state["vy"]
        vel.twist.linear.z = state["vz"]
        vel.twist.angular.x = state["vwx"]
        vel.twist.angular.y = state["vwy"]
        vel.twist.angular.z = state["vwz"]
        self._velocity_pub.publish(vel)

        # Ground truth (same as pose for now)
        self._pose_cov_pub.publish(pose)

        # Vehicle status (for dora dataflow / UE5)
        status = String()
        status.data = f"ARMED jsbsim/c172p pos=({state['lat']:.4f},{state['lon']:.4f},{state['alt']:.1f})"
        self._status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    try:
        node = JSBSimBridge()
        rclpy.spin(node)
    except RuntimeError as e:
        print(f"FATAL: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
