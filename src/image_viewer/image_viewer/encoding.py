"""Image encoding configuration for image_viewer.

Safe to import without OpenCV. Defines the channel count per encoding;
the actual cv2 conversion constants are resolved at runtime.
"""

from typing import Optional

# ── Timing Constants ────────────────────────────────────────────────────────

LIFECYCLE_SERVICE_TIMEOUT_S = 10.0
GET_STATE_TIMEOUT_S = 5.0
OPENCV_WAITKEY_MS = 1

# ── Channel Counts ───────────────────────────────────────────────────────────

RGB_CHANNEL_COUNT = 3
RGBA_CHANNEL_COUNT = 4
MONO_CHANNEL_COUNT = 1

# ── Encoding Map ─────────────────────────────────────────────────────────────

# Maps ROS image encoding string to (channel_count, cv2_conversion_name)
# conversion_name=None means "already BGR, no conversion needed"
ENCODING_CONFIG: dict[str, tuple[int, str | None]] = {
    'rgb8':  (RGB_CHANNEL_COUNT, 'COLOR_RGB2BGR'),
    'bgr8':  (RGB_CHANNEL_COUNT, None),
    'rgba8': (RGBA_CHANNEL_COUNT, 'COLOR_RGBA2BGR'),
    'bgra8': (RGBA_CHANNEL_COUNT, 'COLOR_BGRA2BGR'),
    'mono8': (MONO_CHANNEL_COUNT, None),
}


def resolve_conversion(name: str | None):
    """Resolve a cv2 conversion constant name to its int value."""
    if name is None:
        return None
    import cv2
    return getattr(cv2, name)
