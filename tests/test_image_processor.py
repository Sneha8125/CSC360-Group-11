"""Unit tests for image validation and loading."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tests.helpers import make_image  # noqa: F401  (also sets up sys.path)
from image_processor import load_images, to_rgb, validate_image
from utils import CorruptImageError, InputFileError, UnsupportedFormatError


class ValidateImageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_formats_are_accepted(self):
        for name in ("a.png", "b.jpg", "c.jpeg", "d.bmp", "e.tiff", "f.tif"):
            with self.subTest(name=name):
                path = make_image(self.tmp / name)
                self.assertEqual(validate_image(str(path)), path)

    def test_uppercase_extension_is_accepted(self):
        path = make_image(self.tmp / "UPPER.PNG")
        self.assertEqual(validate_image(str(path)), path)

    def test_missing_file(self):
        with self.assertRaises(InputFileError) as ctx:
            validate_image(str(self.tmp / "nope.png"))
        self.assertIn("does not exist", str(ctx.exception))

    def test_directory_is_rejected(self):
        folder = self.tmp / "folder.png"
        folder.mkdir()
        with self.assertRaises(InputFileError):
            validate_image(str(folder))

    def test_empty_path_is_rejected(self):
        with self.assertRaises(InputFileError):
            validate_image("")

    def test_unsupported_extension(self):
        path = self.tmp / "notes.txt"
        path.write_text("hello")
        with self.assertRaises(UnsupportedFormatError):
            validate_image(str(path))

    def test_corrupted_image_with_valid_extension(self):
        path = self.tmp / "broken.png"
        path.write_bytes(b"this is definitely not a png")
        with self.assertRaises(CorruptImageError):
            validate_image(str(path))

    def test_truncated_image_is_detected(self):
        good = make_image(self.tmp / "good.png", size=(400, 400))
        data = good.read_bytes()
        bad = self.tmp / "truncated.png"
        bad.write_bytes(data[: len(data) // 2])
        with self.assertRaises(CorruptImageError):
            validate_image(str(bad))

    def test_validation_does_not_modify_file(self):
        path = make_image(self.tmp / "keep.png")
        before = path.read_bytes()
        validate_image(str(path))
        self.assertEqual(path.read_bytes(), before)


class LoadImagesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_returns_rgb_image(self):
        path = make_image(self.tmp / "p.png", mode="L", color=128)
        pages = load_images(str(path))
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].mode, "RGB")

    def test_transparent_png_is_flattened_on_white(self):
        path = self.tmp / "alpha.png"
        Image.new("RGBA", (10, 10), (255, 0, 0, 0)).save(path)  # fully transparent
        page = load_images(str(path))[0]
        self.assertEqual(page.getpixel((5, 5)), (255, 255, 255))

    def test_palette_image_with_transparency(self):
        path = self.tmp / "pal.png"
        img = Image.new("P", (10, 10), 0)
        img.info["transparency"] = 0
        img.save(path, transparency=0)
        self.assertEqual(load_images(str(path))[0].mode, "RGB")

    def test_multi_page_tiff_gives_one_image_per_frame(self):
        path = self.tmp / "multi.tiff"
        frames = [Image.new("RGB", (50, 50), c) for c in ("red", "green", "blue")]
        frames[0].save(path, save_all=True, append_images=frames[1:])
        self.assertEqual(len(load_images(str(path))), 3)

    def test_to_rgb_handles_cmyk_and_bilevel(self):
        self.assertEqual(to_rgb(Image.new("CMYK", (4, 4))).mode, "RGB")
        self.assertEqual(to_rgb(Image.new("1", (4, 4))).mode, "RGB")

    def test_sixteen_bit_greyscale(self):
        self.assertEqual(to_rgb(Image.new("I;16", (4, 4))).mode, "RGB")


if __name__ == "__main__":
    unittest.main()
