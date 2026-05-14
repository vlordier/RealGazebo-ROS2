"""Tests for image_viewer encoding configuration.

Tests the ENCODING_CONFIG table and channel constants.
The encoding module requires cv2, so this test skips gracefully if cv2 unavailable.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from image_viewer.encoding import (
        ENCODING_CONFIG, RGB_CHANNEL_COUNT, RGBA_CHANNEL_COUNT, MONO_CHANNEL_COUNT,
        LIFECYCLE_SERVICE_TIMEOUT_S, GET_STATE_TIMEOUT_S, OPENCV_WAITKEY_MS,
    )
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


@unittest.skipIf(not HAS_CV2, "cv2 not available")
class TestEncodingConstants(unittest.TestCase):
    def test_lifecycle_timeout(self):
        self.assertGreater(LIFECYCLE_SERVICE_TIMEOUT_S, 0)
        self.assertLess(LIFECYCLE_SERVICE_TIMEOUT_S, 60)

    def test_get_state_timeout(self):
        self.assertGreater(GET_STATE_TIMEOUT_S, 0)
        self.assertLess(GET_STATE_TIMEOUT_S, 30)

    def test_waitkey_ms(self):
        self.assertEqual(OPENCV_WAITKEY_MS, 1)

    def test_channel_constants(self):
        self.assertEqual(RGB_CHANNEL_COUNT, 3)
        self.assertEqual(RGBA_CHANNEL_COUNT, 4)
        self.assertEqual(MONO_CHANNEL_COUNT, 1)


@unittest.skipIf(not HAS_CV2, "cv2 not available")
class TestEncodingTable(unittest.TestCase):
    def test_has_all_standard_encodings(self):
        self.assertEqual(set(ENCODING_CONFIG.keys()),
                         {'rgb8', 'bgr8', 'rgba8', 'bgra8', 'mono8'})

    def test_channel_counts(self):
        cases = [('rgb8', 3), ('bgr8', 3), ('rgba8', 4), ('bgra8', 4), ('mono8', 1)]
        for enc, expected in cases:
            with self.subTest(enc=enc):
                self.assertEqual(ENCODING_CONFIG[enc][0], expected)

    def test_no_conversion_when_already_bgr(self):
        self.assertIsNone(ENCODING_CONFIG['bgr8'][1])
        self.assertIsNone(ENCODING_CONFIG['mono8'][1])

    def test_conversion_required_when_not_bgr(self):
        self.assertIsNotNone(ENCODING_CONFIG['rgb8'][1])
        self.assertIsNotNone(ENCODING_CONFIG['rgba8'][1])
        self.assertIsNotNone(ENCODING_CONFIG['bgra8'][1])

    def test_unknown_encoding_fallback(self):
        result = ENCODING_CONFIG.get('unknown_enc', (RGB_CHANNEL_COUNT, None))
        self.assertEqual(result[0], 3)
        self.assertIsNone(result[1])

    def test_all_conversions_are_int_constants(self):
        for enc, (_, conv) in ENCODING_CONFIG.items():
            with self.subTest(enc=enc):
                if conv is not None:
                    self.assertIsInstance(conv, int)
                    self.assertGreater(conv, 0)


if __name__ == '__main__':
    unittest.main()
