"""Pydantic v2 data models for RealGazebo dora-rs dataflow.

Provides validated data structures with field constraints for all
messages exchanged in the dora dataflow.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import json


class VehiclePose(BaseModel):
    """3D pose of a vehicle from Gazebo simulation with field validation."""

    x: float = Field(default=0.0, ge=-1e6, le=1e6, description="Position X in meters (NED)")
    y: float = Field(default=0.0, ge=-1e6, le=1e6, description="Position Y in meters (NED)")
    z: float = Field(default=0.0, le=1e6, description="Position Z in meters (NED, negative=up)")
    vx: float = Field(default=0.0, description="Velocity X in m/s")
    vy: float = Field(default=0.0, description="Velocity Y in m/s")
    vz: float = Field(default=0.0, description="Velocity Z in m/s")
    heading: float = Field(default=0.0, ge=-6.29, le=6.29, description="Yaw in radians")
    vehicle_id: int = Field(default=0, ge=0, le=255, description="Vehicle instance ID")
    vehicle_type: str = Field(
        default="unknown",
        pattern=r"^(x500|x500_lidar_2d|lc_62|rover_ackermann|boat|unknown)$",
        description="Vehicle type identifier"
    )
    timestamp_us: int = Field(default=0, ge=0, description="Microseconds since epoch")

    @field_validator('z')
    @classmethod
    def z_should_be_negative_for_up(cls, v: float) -> float:
        if v > 100.0:
            raise ValueError(
                f"z={v} is unusually large — expected NED frame (negative=up)"
            )
        return v

    def to_json(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def from_json(cls, data: bytes) -> "VehiclePose":
        return cls.model_validate_json(data.decode())


class SimulationClock(BaseModel):
    """Simulation clock reading with validation."""

    sec: int = Field(default=0, ge=0, description="Simulation seconds")
    nsec: int = Field(default=0, ge=0, lt=1_000_000_000, description="Nanoseconds within second")
    real_sec: int = Field(default=0, ge=0, description="Real-world seconds")
    real_nsec: int = Field(default=0, ge=0, lt=1_000_000_000, description="Real-world nanoseconds")

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


class VehicleStatus(BaseModel):
    """Vehicle operational status with valid ranges."""

    armed: bool = Field(default=False, description="Whether vehicle is armed")
    nav_state: int = Field(default=0, ge=0, le=31, description="PX4 navigation state ID")
    battery_pct: float = Field(
        default=100.0, ge=0.0, le=100.0, description="Battery remaining percentage"
    )
    flight_mode: str = Field(
        default="UNKNOWN",
        pattern=r"^(MANUAL|ALTCTL|POSCTL|AUTO|OFFBOARD|STAB|UNKNOWN)$",
    )
    vehicle_id: int = Field(default=0, ge=0, le=255)

    def to_json(self) -> bytes:
        return self.model_dump_json().encode()

    @field_validator('flight_mode', mode='before')
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        return v.upper()


class V2VQuality(BaseModel):
    """Vehicle-to-vehicle communication quality metrics."""

    source_id: int = Field(default=0, ge=0, le=255)
    dest_id: int = Field(default=0, ge=0, le=255)
    distance_m: float = Field(default=0.0, ge=0.0, le=1e6)
    rssi_dbm: float = Field(default=0.0, le=0.0, description="RSSI in dBm (always <= 0)")
    packet_loss_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Packet loss rate 0.0-1.0"
    )
    latency_ms: float = Field(default=0.0, ge=0.0, le=1e5)
    jitter_ms: float = Field(default=0.0, ge=0.0, le=1e5)

    def to_json(self) -> bytes:
        return self.model_dump_json().encode()

    @field_validator('rssi_dbm')
    @classmethod
    def rssi_must_be_non_positive(cls, v: float) -> float:
        if v > 0:
            raise ValueError(f"RSSI must be <= 0 dBm, got {v}")
        return v


class VehicleConfig(BaseModel):
    """Validated vehicle entry from YAML configuration."""

    type: str = Field(
        pattern=r"^(x500|x500_lidar_2d|lc_62|rover_ackermann|boat|rock)$"
    )
    firmware: str = Field(
        default="px4", pattern=r"^(px4|ardupilot)$"
    )
    build_target: int = Field(default=0, ge=0)
    spawnpoint: tuple[float, float, float, float] = Field(
        default=(0.0, 0.0, 0.0, 0.0),
        description="(x, y, z, yaw) in NED frame"
    )

    @field_validator('spawnpoint')
    @classmethod
    def validate_spawnpoint(cls, v: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        x, y, z, yaw = v
        if abs(yaw) > 6.29:
            raise ValueError(f"yaw={yaw} out of range [-2pi, 2pi]")
        return v


class SimulationConfig(BaseModel):
    """Top-level simulation configuration from YAML."""

    vehicles: dict[int, VehicleConfig] = Field(default_factory=dict)
