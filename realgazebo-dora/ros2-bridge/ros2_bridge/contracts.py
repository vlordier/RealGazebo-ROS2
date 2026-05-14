"""Single source of truth for RealGazebo data contracts.

All communication formats (ROS2 topics, dora-rs dataflow, UE5 UDP packets)
are derived from these Pydantic models. Never define the same field in
multiple places.

Usage:
    from realgazebo_schema.contracts import VehiclePose
    pose = VehiclePose(x=1.0, y=2.0, z=-5.0)
    ros2_msg = pose.to_ros2_msg()       # → px4_msgs/VehicleLocalPosition
    dora_bytes = pose.to_json()          # → dora-rs dataflow
    udp_packet = pose.to_ue5_packet()    # → bytes for UE5 UDP socket
"""

from pydantic import BaseModel, ConfigDict, Field

# ── Vehicle Pose ─────────────────────────────────────────────────────────────

PACKED_HEADER_FMT = '<BBB'  # vehicle_num, vehicle_code, data_type (struct.pack)


class VehiclePose(BaseModel):
    """3D pose — shared between ROS2, dora, and UE5."""

    model_config = ConfigDict(frozen=True)

    x: float = Field(default=0.0, ge=-1e6, le=1e6)
    y: float = Field(default=0.0, ge=-1e6, le=1e6)
    z: float = Field(default=0.0, le=1e6)
    qw: float = Field(default=1.0, ge=-1.0, le=1.0)
    qx: float = Field(default=0.0, ge=-1.0, le=1.0)
    qy: float = Field(default=0.0, ge=-1.0, le=1.0)
    qz: float = Field(default=0.0, ge=-1.0, le=1.0)
    vehicle_num: int = Field(default=0, ge=0, le=255)
    vehicle_code: int = Field(default=0, ge=0, le=255)

    def to_ue5_packet(self) -> bytes:
        """Serialize to the wire format expected by the UE5 RealGazebo receiver.

        Format matches RealGazebo.cpp sendto() calls:
          header (3 bytes) + 7 floats (x, y, z, qx, qy, qz, qw)
        """
        import struct

        header = struct.pack(PACKED_HEADER_FMT, self.vehicle_num, self.vehicle_code, 1)
        payload = struct.pack('<7f', self.x, self.y, self.z, self.qx, self.qy, self.qz, self.qw)
        return header + payload

    def to_json(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def from_ue5_packet(cls, data: bytes) -> 'VehiclePose | None':
        """Parse a UDP packet from RealGazebo.cpp."""
        import struct

        if len(data) < 3 + 7 * 4:
            return None
        header = struct.unpack(PACKED_HEADER_FMT, data[:3])
        values = struct.unpack('<7f', data[3 : 3 + 7 * 4])
        return cls(
            vehicle_num=header[0],
            vehicle_code=header[1],
            x=values[0],
            y=values[1],
            z=values[2],
            qx=values[3],
            qy=values[4],
            qz=values[5],
            qw=values[6],
        )


class MotorRPM(BaseModel):
    """Motor RPM data — shared between ROS2, dora, and UE5."""

    model_config = ConfigDict(frozen=True)

    vehicle_num: int = Field(default=0, ge=0, le=255)
    vehicle_code: int = Field(default=0, ge=0, le=255)
    rpm_values: list[float] = Field(default_factory=list, max_length=16)

    def to_ue5_packet(self) -> bytes:
        import struct

        n = len(self.rpm_values)
        header = struct.pack(PACKED_HEADER_FMT, self.vehicle_num, self.vehicle_code, 2)
        payload = struct.pack(f'<{n}f', *self.rpm_values)
        return header + payload


class SimReset(BaseModel):
    """Reset signal sent by RealGazebo plugin on configure/shutdown."""

    model_config = ConfigDict(frozen=True)

    vehicle_num: int = Field(default=0, ge=0, le=255)
    vehicle_code: int = Field(default=0, ge=0, le=255)

    def to_ue5_packet(self) -> bytes:
        import struct

        return struct.pack(PACKED_HEADER_FMT, self.vehicle_num, self.vehicle_code, 4)


# ── Data Type Registry ──────────────────────────────────────────────────────

# Maps the `data_type` byte in RealGazebo UDP packets to their model
UE5_DATA_TYPES: dict[int, type[BaseModel]] = {
    1: VehiclePose,
    2: MotorRPM,
    4: SimReset,
}


def parse_ue5_packet(data: bytes) -> BaseModel | None:
    """Parse any RealGazebo UDP packet into its typed model."""
    import struct

    if len(data) < 3:
        return None
    dtype = struct.unpack(PACKED_HEADER_FMT, data[:3])[2]
    model_cls = UE5_DATA_TYPES.get(dtype)
    if model_cls is None:
        return None
    if dtype == 1:
        return VehiclePose.from_ue5_packet(data)
    if dtype == 4:
        hdr = struct.unpack(PACKED_HEADER_FMT, data[:3])
        return SimReset(vehicle_num=hdr[0], vehicle_code=hdr[1])
    return None
