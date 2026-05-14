"""Image encoding configuration for image_viewer.

Maps ROS image encodings to (channel_count, cv2_conversion_flag).
Both cv2 and its constants are required at import time — this is
intentional: if cv2 isn't available, the user gets a clear ImportError
at startup rather than a silent fallback at runtime.
"""

import cv2

# ── Timing Constants ────────────────────────────────────────────────────────

LIFECYCLE_SERVICE_TIMEOUT_S = 10.0
GET_STATE_TIMEOUT_S = 5.0
OPENCV_WAITKEY_MS = 1

# ── Channel Counts ───────────────────────────────────────────────────────────

RGB_CHANNEL_COUNT = 3
RGBA_CHANNEL_COUNT = 4
MONO_CHANNEL_COUNT = 1

# ── Encoding Map ─────────────────────────────────────────────────────────────

# (channel_count, cv2_color_conversion_flag | None)
# None means "already BGR, no conversion needed"
ENCODING_CONFIG: dict[str, tuple[int, int | None]] = {
    'rgb8': (RGB_CHANNEL_COUNT, cv2.COLOR_RGB2BGR),
    'bgr8': (RGB_CHANNEL_COUNT, None),
    'rgba8': (RGBA_CHANNEL_COUNT, cv2.COLOR_RGBA2BGR),
    'bgra8': (RGBA_CHANNEL_COUNT, cv2.COLOR_BGRA2BGR),
    'mono8': (MONO_CHANNEL_COUNT, None),
}
