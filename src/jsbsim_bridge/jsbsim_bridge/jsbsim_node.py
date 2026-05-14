#!/usr/bin/env python3
"""JSBSim Flight Dynamics Model bridge for RealGazebo.

Loads a JSBSim aircraft model, steps the simulation at a fixed rate,
and publishes aircraft state as ROS2 topics. Subscribes to actuator
commands for flight control surface inputs.

Usage:
    ros2 run jsbsim_bridge jsbsim_node --ros-args \
        -p aircraft:=x8 -p update_rate:=250

Published topics:
    /jsbsim/pose              geometry_msgs/PoseStamped
    /jsbsim/velocity          geometry_msgs/TwistStamped
    /jsbsim/state             fdm_msgs/FDMState (custom)

Subscribed topics:
    /jsbsim/controls          std_msgs/Float64MultiArray  [throttle, elevator, aileron, rudder]
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped, TwistStamped
from std_msgs.msg import Float64MultiArray
import math
import os
import threading

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_AIRCRAFT = "c172p"
DEFAULT_UPDATE_RATE_HZ = 250
DEFAULT_FRAME_ID = "map"
CONTROLS_TIMEOUT_S = 1.0

# JSBSim internal property paths for control inputs
JSBSIM_PROPERTIES = {
    "lat": "position/lat-geod-rad",
    "lon": "position/long-gc-rad",
    "alt": "position/h-sl-meters",
    "phi": "attitude/phi-rad",
    "theta": "attitude/theta-rad",
    "psi": "attitude/psi-rad",
    "v_north": "velocity/v-north-fps",
    "v_east": "velocity/v-east-fps",
    "v_down": "velocity/v-down-fps",
    "pitch_rate": "attitude/pitch-rate-rad_sec",
    "roll_rate": "attitude/roll-rate-rad_sec",
    "yaw_rate": "attitude/yaw-rate-rad_sec",
}


class JSBSimBridge(Node):
    """Bridges JSBSim FDM to ROS2 topics.

    Architecture:
        JSBSim FDM ──(sim step)──▶ PoseStamped, TwistStamped
        ROS2 controls ──────────────▶ fcs/throttle-cmd-norm, etc.
    """

    def __init__(self):
        super().__init__("jsbsim_bridge")

        # Parameters
        self.declare_parameter("aircraft", DEFAULT_AIRCRAFT)
        self.declare_parameter("update_rate", DEFAULT_UPDATE_RATE_HZ)
        self.declare_parameter("frame_id", DEFAULT_FRAME_ID)

        aircraft = self.get_parameter("aircraft").value
        self._update_interval_s = 1.0 / self.get_parameter("update_rate").value
        self._frame_id = self.get_parameter("frame_id").value

        # Initialize JSBSim
        self._fdm = self._init_jsbsim(aircraft)
        if self._fdm is None:
            raise RuntimeError(f"Failed to load JSBSim aircraft: {aircraft}")

        # Publishers
        self._pose_pub = self.create_publisher(PoseStamped, "/jsbsim/pose", 10)
        self._velocity_pub = self.create_publisher(TwistStamped, "/jsbsim/velocity", 10)

        # Subscribers
        self._control_sub = self.create_subscription(
            Float64MultiArray, "/jsbsim/controls",
            self._control_callback, 10
        )
        self._latest_controls = [0.0, 0.0, 0.0, 0.0]
        self._controls_lock = threading.Lock()

        # Simulation timer
        self._sim_thread = threading.Thread(target=self._sim_loop, daemon=True)
        self._sim_running = True
        self._sim_thread.start()

        self.get_logger().info(
            f"[jsbsim] Loaded {aircraft} at {self.get_parameter('update_rate').value} Hz"
        )

    def _init_jsbsim(self, aircraft: str):
        """Initialize JSBSim FDM with the given aircraft model."""
        try:
            import jsbsim
            root = jsbsim.get_default_root_dir()
            fdm = jsbsim.FGFDMExec(root, None)
            fdm.load_model(aircraft)
            fdm.set_dt(self._update_interval_s)
            fdm.run_ic()
            fdm.run()
            self.get_logger().info(f"[jsbsim] Aircraft {aircraft} initialized")
            return fdm
        except Exception as e:
            self.get_logger().error(f"[jsbsim] Init failed: {e}")
            return None

    def _control_callback(self, msg: Float64MultiArray):
        """Store latest control surface commands."""
        with self._controls_lock:
            n = min(len(msg.data), len(self._latest_controls))
            self._latest_controls[:n] = msg.data[:n]

    def _sim_loop(self):
        """Run JSBSim simulation loop at the configured update rate."""
        import rclpy
        while self._sim_running and rclpy.ok():
            self._step()
            self._fdm.run()
            rclpy.spin_once(self, timeout_sec=0)

    def _step(self):
        """Apply controls and publish state."""
        fdm = self._fdm
        if fdm is None:
            return

        # Apply latest control inputs
        with self._controls_lock:
            props = fdm.get_property_catalog()
            for i, prop in enumerate(CONTROL_PROPERTIES):
                if i < len(self._latest_controls):
                    try:
                        fdm[prop] = self._latest_controls[i]
                    except KeyError:
                        pass

        # Read aircraft state
        lat = fdm["position/lat-gc-rad"] * 180.0 / math.pi
        lon = fdm["position/lon-gc-rad"] * 180.0 / math.pi
        alt = fdm["position/h-sl-meters"]
        phi = fdm["attitude/phi-rad"]
        theta = fdm["attitude/theta-rad"]
        psi = fdm["attitude/psi-rad"]

        v_north = fdm["velocity/v-north-fps"] * 0.3048  # fps → m/s
        v_east = fdm["velocity/v-east-fps"] * 0.3048
        v_down = fdm["velocity/v-down-fps"] * 0.3048

        # Publish pose
        pose_msg = PoseStamped()
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = self._frame_id
        pose_msg.pose.position.x = lon
        pose_msg.pose.position.y = lat
        pose_msg.pose.position.z = alt
        # Simplified quaternion from euler (roll/pitch/yaw)
        cy = math.cos(psi * 0.5)
        sy = math.sin(psi * 0.5)
        cp = math.cos(theta * 0.5)
        sp = math.sin(theta * 0.5)
        cr = math.cos(phi * 0.5)
        sr = math.sin(phi * 0.5)
        pose_msg.pose.orientation.w = cr * cp * cy + sr * sp * sy
        pose_msg.pose.orientation.x = sr * cp * cy - cr * sp * sy
        pose_msg.pose.orientation.y = cr * sp * cy + sr * cp * sy
        pose_msg.pose.orientation.z = cr * cp * sy - sr * sp * cy
        self._pose_pub.publish(pose_msg)

        # Publish velocity
        vel_msg = TwistStamped()
        vel_msg.header.stamp = pose_msg.header.stamp
        vel_msg.header.frame_id = self._frame_id
        vel_msg.twist.linear.x = v_north
        vel_msg.twist.linear.y = v_east
        vel_msg.twist.linear.z = v_down
        vel_msg.twist.angular.x = fdm["attitude/pitch-rate-rad_sec"]
        vel_msg.twist.angular.y = fdm["attitude/roll-rate-rad_sec"]
        vel_msg.twist.angular.z = fdm["attitude/yaw-rate-rad_sec"]
        self._velocity_pub.publish(vel_msg)

        self.get_logger().debug(
            f"[jsbsim] pos=({lat:.4f}, {lon:.4f}, {alt:.1f}) "
            f"vel=({v_north:.1f}, {v_east:.1f}, {v_down:.1f})"
        )

    def destroy_node(self):
        self._sim_running = False
        if self._sim_thread.is_alive():
            self._sim_thread.join(timeout=2.0)
        super().destroy_node()


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
