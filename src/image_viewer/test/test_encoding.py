"""Tests for image_viewer encoding configuration.

Tests the ENCODING_CONFIG table and channel constants
which are importable without ROS2 or OpenCV dependencies.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from image_viewer.encoding import (
    ENCODING_CONFIG, RGB_CHANNEL_COUNT, RGBA_CHANNEL_COUNT, MONO_CHANNEL_COUNT,
    LIFECYCLE_SERVICE_TIMEOUT_S, GET_STATE_TIMEOUT_S, OPENCV_WAITKEY_MS,
    resolve_conversion,
)


class TestEncodingConstants(unittest.TestCase):
    """Test timing and channel constants."""

    def test_lifecycle_timeout_sane(self):
        self.assertGreater(LIFECYCLE_SERVICE_TIMEOUT_S, 0)
        self.assertLess(LIFECYCLE_SERVICE_TIMEOUT_S, 60)

    def test_get_state_timeout_sane(self):
        self.assertGreater(GET_STATE_TIMEOUT_S, 0)
        self.assertLess(GET_STATE_TIMEOUT_S, 30)

    def test_waitkey_ms_sane(self):
        self.assertEqual(OPENCV_WAITKEY_MS, 1)

    def test_channel_constants(self):
        self.assertEqual(RGB_CHANNEL_COUNT, 3)
        self.assertEqual(RGBA_CHANNEL_COUNT, 4)
        self.assertEqual(MONO_CHANNEL_COUNT, 1)


class TestEncodingTable(unittest.TestCase):
    """Test the ENCODING_CONFIG table structure."""

    def test_all_encodings_have_valid_structure(self):
        for enc, (ch, conv_name) in ENCODING_CONFIG.items():
            with self.subTest(enc=enc):
                self.assertIsInstance(ch, int)
                self.assertGreater(ch, 0)
                self.assertLessEqual(ch, 4)
                self.assertTrue(conv_name is None or isinstance(conv_name, str))

    def test_knows_all_standard_encodings(self):
        expected = {'rgb8', 'bgr8', 'rgba8', 'bgra8', 'mono8'}
        self.assertEqual(set(ENCODING_CONFIG.keys()), expected)

    def test_rgb8_channels(self):
        self.assertEqual(ENCODING_CONFIG['rgb8'][0], 3)

    def test_bgr8_channels(self):
        self.assertEqual(ENCODING_CONFIG['bgr8'][0], 3)

    def test_rgba8_channels(self):
        self.assertEqual(ENCODING_CONFIG['rgba8'][0], 4)

    def test_bgra8_channels(self):
        self.assertEqual(ENCODING_CONFIG['bgra8'][0], 4)

    def test_mono8_channels(self):
        self.assertEqual(ENCODING_CONFIG['mono8'][0], 1)

    def test_bgr8_no_conversion(self):
        self.assertIsNone(ENCODING_CONFIG['bgr8'][1])

    def test_mono8_no_conversion(self):
        self.assertIsNone(ENCODING_CONFIG['mono8'][1])

    def test_rgb8_has_conversion(self):
        self.assertIsNotNone(ENCODING_CONFIG['rgb8'][1])

    def test_unknown_encoding_fallback(self):
        result = ENCODING_CONFIG.get('unknown_enc', (RGB_CHANNEL_COUNT, None))
        channels, conv = result
        self.assertEqual(channels, 3)
        self.assertIsNone(conv)

    def test_rgb_encodings_have_3_channels(self):
        for enc, (ch, _) in ENCODING_CONFIG.items():
            if 'rgb' in enc and 'a' not in enc:
                self.assertEqual(ch, 3, f"{enc} should be 3 channels")

    def test_rgba_encodings_have_4_channels(self):
        for enc, (ch, _) in ENCODING_CONFIG.items():
            if 'rgba' in enc or 'bgra' in enc:
                self.assertEqual(ch, 4, f"{enc} should be 4 channels")


class TestResolveConversion(unittest.TestCase):
    """Test the cv2 constant resolver (without needing cv2)."""

    def test_none_returns_none(self):
        self.assertIsNone(resolve_conversion(None))

    def test_invalid_name_raises(self):
        with self.assertRaises((AttributeError, ImportError)):
            resolve_conversion("NONEXISTENT_CONSTANT")


if __name__ == '__main__':
    unittest.main()
