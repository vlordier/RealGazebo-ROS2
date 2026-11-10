# Configuration

## Vehicle YAML Format

```yaml
vehicles:
  0:
    type: x500                    # Vehicle model: x500, lc_62, rover_ackermann, boat
    firmware: px4                 # Flight controller: px4, ardupilot, jsbsim
    build_target: 0               # PX4 build target index
    spawnpoint: (0, 0, 0, 0)      # (x, y, z, yaw) in NED frame
```

## Config Example (10 vehicles)

See `src/realgazebo/yaml/example.yaml` for a complete multi-vehicle setup with:
- 5 x500 quadrotors (PX4)
- 1 lc_62 VTOL (PX4)
- 3 rover_ackermann (ArduPilot)
- 2 boats (PX4)

## Spawn Points

Coordinates are in the **NED** (North-East-Down) frame relative to world origin.
Yaw is in radians (`-π` to `π`).

## Validation

Configs are validated by Pydantic when loaded. Invalid types or firmware values
raise clear errors at load time.
