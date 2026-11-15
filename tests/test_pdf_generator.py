"""Unit tests for page layout and PDF generation."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from tests.helpers import make_image, pdf_page_count
from pdf_generator import A4_PORTRAIT, MARGIN_PX, fit_to_page, generate_pdf, page_size_for
from utils import OutputPathError


class FitToPageTests(unittest.TestCase):
    def test_portrait_image_gets_portrait_page(self):
        page = fit_to_page(Image.new("RGB", (400, 800)))
        self.assertEqual(page.size, A4_PORTRAIT)

    def test_landscape_image_gets_landscape_page(self):
        page = fit_to_page(Image.new("RGB", (800, 400)))
        self.assertEqual(page.size, (A4_PORTRAIT[1], A4_PORTRAIT[0]))

    def test_square_image_gets_portrait_page(self):
        self.assertEqual(page_size_for(Image.new("RGB", (500, 500))), A4_PORTRAIT)

    def test_image_is_inside_margins_and_centred(self):
        page = fit_to_page(Image.new("RGB", (1000, 1000), (0, 0, 0)))
        w, h = page.size
        # Corners / margin are white, centre is the (black) image.
        self.assertEqual(page.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(page.getpixel((MARGIN_PX - 5, h // 2)), (255, 255, 255))
        self.assertEqual(page.getpixel((w // 2, h // 2)), (0, 0, 0))

    def test_aspect_ratio_is_preserved(self):
        src = Image.new("RGB", (300, 100), (0, 0, 0))
        page = fit_to_page(src)
        # Find bounding box of non-white pixels.
        bbox = page.convert("L").point(lambda v: 255 if v < 128 else 0).getbbox()
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        self.assertAlmostEqual(width / height, 3.0, delta=0.05)

    def test_large_image_is_scaled_down_to_fit(self):
        page = fit_to_page(Image.new("RGB", (6000, 4000)))
        self.assertEqual(page.size, (A4_PORTRAIT[1], A4_PORTRAIT[0]))


class GeneratePdfTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_valid_pdf(self):
        out = self.tmp / "out.pdf"
        generate_pdf([Image.new("RGB", (200, 100), "red")], out)
        data = out.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", data)

    def test_one_page_per_image(self):
        out = self.tmp / "multi.pdf"
        images = [Image.new("RGB", (200, 100), c) for c in ("red", "green", "blue")]
        generate_pdf(images, out)
        self.assertEqual(pdf_page_count(out), 3)

    def test_mixed_orientations(self):
        out = self.tmp / "mixed.pdf"
        generate_pdf([Image.new("RGB", (100, 300)), Image.new("RGB", (300, 100))], out)
        self.assertEqual(pdf_page_count(out), 2)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            generate_pdf([], self.tmp / "x.pdf")

    def test_unwritable_location_raises_and_leaves_no_temp_file(self):
        out = self.tmp / "missing_dir" / "x.pdf"  # parent does not exist
        with self.assertRaises(OutputPathError):
            generate_pdf([Image.new("RGB", (10, 10))], out)
        self.assertFalse(out.exists())
        self.assertFalse(out.with_name("x.pdf.tmp").exists())

    def test_source_image_is_untouched(self):
        src = make_image(self.tmp / "src.png")
        before = src.read_bytes()
        generate_pdf([Image.open(src).convert("RGB")], self.tmp / "o.pdf")
        self.assertEqual(src.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
