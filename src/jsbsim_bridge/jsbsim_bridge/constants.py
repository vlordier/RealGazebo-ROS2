"""Constants and property paths for JSBSim bridge.

Safe to import without rclpy.
"""

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_AIRCRAFT = 'c172p'
DEFAULT_UPDATE_RATE_HZ = 250
DEFAULT_FRAME_ID = 'map'

FPS_TO_MPS = 0.3048

# JSBSim property paths for state reading (single source of truth)
JSBSIM_PROPERTIES = {
    'lat': 'position/lat-geod-rad',
    'lon': 'position/long-gc-rad',
    'alt': 'position/h-sl-meters',
    'phi': 'attitude/phi-rad',
    'theta': 'attitude/theta-rad',
    'psi': 'attitude/psi-rad',
    'v_north': 'velocities/v-north-fps',
    'v_east': 'velocities/v-east-fps',
    'v_down': 'velocities/v-down-fps',
    'throttle': 'fcs/throttle-cmd-norm',
    'elevator': 'fcs/elevator-cmd-norm',
    'aileron': 'fcs/aileron-cmd-norm',
    'rudder': 'fcs/rudder-cmd-norm',
}
