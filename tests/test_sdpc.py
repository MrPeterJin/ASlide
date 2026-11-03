"""SDPC region regression tests; no native SDK or slide files required.

Run with: python -m unittest discover -s tests -v
"""

import ctypes
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from PIL import Image


class SdpcReadRegionTests(unittest.TestCase):
    def setUp(self):
        # Load the actual backend with only its native bindings replaced.
        # Avoid importing Aslide.__init__ and unrelated optional backends.
        bindings = types.ModuleType("_sdpc_test.sdpc_bindings")
        self.sdk = types.SimpleNamespace(sqrayslide_read_region_bgra=self.read)
        bindings.sdpc_sdk = self.sdk
        bindings.SDPCError = types.SimpleNamespace(SqSuccess=0)
        bindings.SDPCWSIType = types.SimpleNamespace()
        bindings.ColorStyle = types.SimpleNamespace()
        bindings.c_int32 = ctypes.c_int32
        source = Path(__file__).resolve().parents[1] / "Aslide/sdpc/sdpc_slide.py"
        spec = importlib.util.spec_from_file_location("_sdpc_test.sdpc_slide", source)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {bindings.__name__: bindings}):
            spec.loader.exec_module(module)
        self.slide = module.SdpcSlide.__new__(module.SdpcSlide)
        self.slide.slide = object()
        self.slide._closed = False
        self.slide._level_count = 3
        self.slide._level_downsamples = (1.0, 2.0, 4.0)
        self.calls = []
        self.buffers = []
        self.fourth_byte = None
        self.success = True

    def tearDown(self):
        # The fake handle is not a native slide and must not be closed by SDK.
        self.slide.slide = None
        self.slide._closed = True

    @staticmethod
    def rgb(index):
        return ((index * 29 + 177) % 256,
                (index * 13 + 91) % 256,
                (index * 7) % 256)

    def read(self, handle, buffer, x, y, width, height, level):
        self.calls.append((x, y, width, height, level))
        self.buffers.append(buffer)
        self.assertEqual(bytes(buffer), bytes(width * height * 4))
        for i in range(width * height):
            r, g, b = self.rgb(i)
            fourth = i % 256 if self.fourth_byte is None else self.fourth_byte
            buffer[4 * i:4 * i + 4] = (b, g, r, fourth)
        return self.success

    def test_rgb_pixels_sizes_and_row_order(self):
        for size in ((1, 1), (3, 5), (64, 129), (256, 256)):
            with self.subTest(size=size):
                image = self.slide.read_region((0, 0), 0, size)
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, size)
                expected = bytes(v for i in range(size[0] * size[1])
                                 for v in self.rgb(i))
                self.assertEqual(image.tobytes(), expected)

    def test_fourth_byte_is_discarded(self):
        outputs = []
        for fourth in (0, 17, 255, None):
            self.fourth_byte = fourth
            outputs.append(self.slide.read_region((0, 0), 0, (19, 17)).tobytes())
        self.assertTrue(all(output == outputs[0] for output in outputs))

    def test_image_owns_pixels_after_buffer_mutation_and_next_read(self):
        image = self.slide.read_region((0, 0), 0, (17, 11))
        expected = image.tobytes()
        ctypes.memset(self.buffers[-1], 255, len(self.buffers[-1]))
        self.slide.read_region((0, 0), 0, (17, 11))
        self.buffers.clear()
        self.assertEqual(image.tobytes(), expected)

    def test_level_zero_coordinates_are_scaled(self):
        self.slide.read_region((803, 407), 2, (3, 5))
        self.assertEqual(self.calls, [(200, 101, 3, 5, 2)])

    def test_invalid_parameters_do_not_call_sdk(self):
        for level in (-1, 3):
            with self.assertRaisesRegex(ValueError, f"^Invalid level: {level}$"):
                self.slide.read_region((0, 0), level, (4, 4))
        for size in ((0, 4), (4, 0), (-1, 4)):
            with self.assertRaises(ValueError) as error:
                self.slide.read_region((0, 0), 0, size)
            self.assertEqual(str(error.exception), f"Invalid size: {size}")
        self.assertEqual(self.calls, [])

    def test_closed_slide_does_not_call_sdk(self):
        self.slide._closed = True
        with self.assertRaisesRegex(RuntimeError, "^Slide has been closed$"):
            self.slide.read_region((0, 0), 0, (4, 4))
        self.assertEqual(self.calls, [])

    def test_sdk_failure_keeps_error_context(self):
        self.success = False
        with self.assertRaises(RuntimeError) as error:
            self.slide.read_region((803, 407), 2, (3, 5))
        self.assertEqual(str(error.exception),
                         "Failed to read region at level-0 coords (803, 407) "
                         "-> level-2 coords (200, 101) with size (3, 5)")


class _Slide:
    level_dimensions = ((16, 16),)
    level_downsamples = (1.0,)
    dimensions = (16, 16)
    properties = {}

    def __init__(self, mode):
        self.mode = mode

    def get_best_level_for_downsample(self, downsample):
        return 0

    def read_region(self, location, level, size):
        if self.mode == "RGB":
            return Image.new("RGB", size, (47, 89, 131))
        return Image.new("RGBA", size, (47, 89, 131, 128))


def _deepzoom_class():
    pkg = types.ModuleType("Aslide")
    pkg.__path__ = []
    sub = types.ModuleType("Aslide.sdpc")
    sub.__path__ = []
    slide = types.ModuleType("Aslide.sdpc.sdpc_slide")
    slide.SdpcSlide = _Slide
    source = Path(__file__).resolve().parents[1] / "Aslide/sdpc/sdpc_deepzoom.py"
    spec = importlib.util.spec_from_file_location("Aslide.sdpc.sdpc_deepzoom", source)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"Aslide": pkg, "Aslide.sdpc": sub,
                                  "Aslide.sdpc.sdpc_slide": slide}):
        spec.loader.exec_module(module)
    return module.DeepZoomGenerator


class SdpcDeepZoomTests(unittest.TestCase):
    def test_rgb_tile_preserves_opaque_pixels_without_compositing(self):
        generator = _deepzoom_class()(_Slide("RGB"), tile_size=8, overlap=0)
        with patch("PIL.Image.composite", side_effect=AssertionError("unneeded composite")):
            tile = generator.get_tile(generator.level_count - 1, (0, 0))
        self.assertEqual(tile.mode, "RGB")
        self.assertEqual(tile.size, (8, 8))
        self.assertEqual(tile.getpixel((4, 4)), (47, 89, 131))

    def test_rgba_tile_still_uses_its_alpha_to_composite(self):
        generator = _deepzoom_class()(_Slide("RGBA"), tile_size=8, overlap=0)
        tile = generator.get_tile(generator.level_count - 1, (0, 0))
        expected = Image.composite(Image.new("RGBA", (8, 8), (47, 89, 131, 128)),
                                   Image.new("RGB", (8, 8), "white"),
                                   Image.new("RGBA", (8, 8), (47, 89, 131, 128)))
        self.assertEqual(tile.mode, "RGB")
        self.assertEqual(tile.tobytes(), expected.tobytes())


if __name__ == "__main__":
    unittest.main()
