# UE5 Weather & Time-of-Day Setup

RealGazebo sends a `data_type=6` simulation info packet every ~1 second
containing the simulation time and geolocation. Your UE5 project can use
this data to drive realistic sky, sun, clouds, and exposure.

## Packet Format (data_type = 6)

```
[header: vehicle_num, vehicle_code, data_type=6] = 3 bytes
+ sim_time_sec    (uint64_t, 8 bytes)  — seconds since sim start
+ sim_time_nsec   (uint32_t, 4 bytes)  — nanoseconds remainder
+ latitude_deg    (float,   4 bytes)   — e.g. 36.728
+ longitude_deg   (float,   4 bytes)   — e.g. 127.444
+ altitude        (float,   4 bytes)   — meters AMSL
= 23 bytes total
```

## UE5 Blueprint Setup

### 1. Enable Required Plugins

- **Georeferencing** — for lat/lon→UE coordinate conversion
- **Sun Position Calculator** — for physical sun position

Restart the editor after enabling.

### 2. Create the Level

1. New **Empty Level** (no Open World support needed for c-track)
2. Enable **Large World Coordinates** in World Settings
3. Drop a **Georeferencing System** actor, set origin to match c-track:
   - Latitude: `36.728` / Longitude: `127.444` / Altitude: `68.9`
4. Drop a **SunSky** actor
   - Set its georeference to the same origin
   - Set time zone to `Asia/Seoul` (UTC+9)
   - Compass north offset: `-90` (Cesium/ESRI north is -Y)

### 3. Receive RealGazebo UDP in Blueprints

Create an `ARxUdp`-style Actor (or use the standalone `ue5_receiver` as reference):

1. Open your Level Blueprint
2. Create a `UDP Socket` (or use File/Networking plugin)
3. Bind to port `5005`
4. On received data:
   - Read 3-byte header (vehicle_code, vehicle_num, data_type)
   - If `data_type == 6`:
     - Read `uint64 sim_sec`, `uint32 sim_nsec`, `float lat`, `float lon`, `float alt`
     - Compute total seconds: `sim_sec + sim_nsec / 1e9`
     - **Set SunSky time of day** to `total_seconds % 86400` (mod 24h)
     - Optionally update Georeferencing origin if lat/lon change

### 4. Weather & Sky

Add a **Volumetric Clouds** component to the SunSky actor:

- Create a **Material Instance** from the default cloud material
- Tweak for more "noisy" look:
  - Density: `0.4`
  - Coverage: `0.6`
  - Noise scale: `50000`
  - Shape noise scale: `25000`

### 5. Exposure Control

1. Drop a **PostProcessVolume** with **Infinite Extent**
2. Under Exposure:
   - Set **Min EV** to `13.5`
   - Adjust **Eye Adaptation Speed** to taste (`0.5`–`1.0`)
3. This prevents the engine from over-brightening at night/dusk

### 6. Virtual Shadow Maps

Select the SunSky's Directional Light component:

- Enable **Cast Shadows**
- Set **Dynamic Shadow Distance** to `200000` (2 km)
- UE5 Virtual Shadow Maps handle this efficiently

## Gazebo SDF Configuration

The c-track world (`src/realgazebo/worlds/c-track.sdf`) already includes:

```xml
<spherical_coordinates>
  <latitude_deg>36.72804033</latitude_deg>
  <longitude_deg>127.44368483</longitude_deg>
  <elevation>68.900</elevation>
</spherical_coordinates>
```

The RealGazebo plugin forwards these coordinates in the sim info packet.
You can override them per-model in the SDF template by adding:

```xml
<latitude_deg>48.8566</latitude_deg>
<longitude_deg>2.3522</longitude_deg>
<altitude>35.0</altitude>
```

## Testing

Run the standalone receiver to verify packets are flowing:

```bash
cd src/RealGazeboUE5
g++ -std=c++17 -o ue5_receiver ue5_receiver.cpp
./ue5_receiver
```

Expected output every ~1 second:

```
[172.20.0.10] type=6 SIM_INFO sim_time=123.456s lat=36.728 lon=127.444 alt=68.9
```
