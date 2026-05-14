"""Pydantic v2 data models for RealGazebo dora-rs dataflow.

Provides validated, immutable data structures with field constraints.
Uses strict mode for type enforcement and frozen=True to prevent
accidental mutation.
"""


from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehiclePose(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    x: float = Field(default=0.0, ge=-1e6, le=1e6)
    y: float = Field(default=0.0, ge=-1e6, le=1e6)
    z: float = Field(default=0.0, le=1e6)
    vx: float = Field(default=0.0)
    vy: float = Field(default=0.0)
    vz: float = Field(default=0.0)
    heading: float = Field(default=0.0, ge=-6.29, le=6.29)
    vehicle_id: int = Field(default=0, ge=0, le=255)
    vehicle_type: str = Field(
        default="unknown",
        pattern=r"^(x500|x500_lidar_2d|lc_62|rover_ackermann|boat|unknown)$",
    )
    timestamp_us: int = Field(default=0, ge=0)

    @field_validator('z')
    @classmethod
    def z_must_be_ned(cls, v: float) -> float:
        if v > 100.0:
            raise ValueError(f"z={v} too large — expected NED frame (negative=up)")
        return v

    def to_json(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def from_json(cls, data: bytes) -> "VehiclePose":
        return cls.model_validate_json(data.decode())


class SimulationClock(BaseModel):
    model_config = ConfigDict(frozen=True)

    sec: int = Field(default=0, ge=0)
    nsec: int = Field(default=0, ge=0, lt=1_000_000_000)
    real_sec: int = Field(default=0, ge=0)
    real_nsec: int = Field(default=0, ge=0, lt=1_000_000_000)

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
    model_config = ConfigDict(frozen=True)

    armed: bool = Field(default=False)
    nav_state: int = Field(default=0, ge=0, le=31)
    battery_pct: float = Field(default=100.0, ge=0.0, le=100.0)
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
    model_config = ConfigDict(frozen=True, strict=True)

    source_id: int = Field(default=0, ge=0, le=255)
    dest_id: int = Field(default=0, ge=0, le=255)
    distance_m: float = Field(default=0.0, ge=0.0, le=1e6)
    rssi_dbm: float = Field(default=0.0, le=0.0)
    packet_loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
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
    model_config = ConfigDict(frozen=True)

    type: str = Field(pattern=r"^(x500|x500_lidar_2d|lc_62|rover_ackermann|boat|rock)$")
    firmware: str = Field(default="px4", pattern=r"^(px4|ardupilot|jsbsim)$")
    build_target: int = Field(default=0, ge=0)
    spawnpoint: tuple[float, float, float, float] = Field(
        default=(0.0, 0.0, 0.0, 0.0),
    )

    @field_validator('spawnpoint')
    @classmethod
    def yaw_in_range(cls, v: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        _, _, _, yaw = v
        if abs(yaw) > 6.29:
            raise ValueError(f"yaw={yaw} out of range [-2pi, 2pi]")
        return v
