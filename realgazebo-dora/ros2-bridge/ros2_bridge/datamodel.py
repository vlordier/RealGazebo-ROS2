"""Dora operators for RealGazebo dataflow.

Provides typed data structures and operator patterns for bridging
ROS2 topics into the dora-rs dataflow.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
import json
import logging

logger = logging.getLogger("realgazebo.dora")

# ── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class VehiclePose:
    """3D pose of a vehicle from Gazebo simulation."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    heading: float = 0.0
    vehicle_id: int = 0
    vehicle_type: str = "unknown"
    timestamp_us: int = 0

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_json(cls, data: bytes) -> "VehiclePose":
        return cls(**json.loads(data.decode()))


@dataclass
class SimulationClock:
    """Simulation clock reading."""
    sec: int = 0
    nsec: int = 0
    real_sec: int = 0
    real_nsec: int = 0

    @property
    def sim_time_s(self) -> float:
        return self.sec + self.nsec / 1e9

    @property
    def real_time_s(self) -> float:
        return self.real_sec + self.real_nsec / 1e9

    @property
    def speed_factor(self) -> float:
        if self.real_time_s > 0:
            return self.sim_time_s / self.real_time_s
        return 1.0


@dataclass
class VehicleStatus:
    """Vehicle operational status from PX4/ArduPilot."""
    armed: bool = False
    nav_state: int = 0
    battery_pct: float = 100.0
    flight_mode: str = "UNKNOWN"
    vehicle_id: int = 0

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()


@dataclass
class V2VQuality:
    """Vehicle-to-vehicle communication quality."""
    source_id: int = 0
    dest_id: int = 0
    distance_m: float = 0.0
    rssi_dbm: float = 0.0
    packet_loss_rate: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()


# ── Helpers ──────────────────────────────────────────────────────────────────


def safe_send(dora_node, output_id: str, data: bytes) -> None:
    """Send data to a dora output, catching and logging errors."""
    try:
        dora_node.send_output(output_id, data)
    except Exception as e:
        logger.error(f"Failed to send to {output_id}: {e}")


def event_id(event) -> str:
    """Safely extract event ID."""
    try:
        return event.get("id", "unknown") if hasattr(event, "get") else str(event.id)
    except Exception:
        return "unknown"


def event_value(event) -> Optional[bytes]:
    """Safely extract event value as bytes."""
    try:
        val = event["value"]
        if val and len(val) > 0:
            return val[0]
        return None
    except Exception:
        return None
