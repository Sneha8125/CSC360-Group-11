"""Unit tests for path / output-name helpers."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_image  # noqa: F401
from utils import (
    OutputExistsError,
    OutputPathError,
    default_output_name,
    ensure_not_input,
    has_supported_extension,
    prepare_output_path,
    resolve_output_path,
)


class OutputNameTests(unittest.TestCase):
    def test_single_image_uses_its_stem(self):
        self.assertEqual(default_output_name([Path("abc.png")]), "abc.pdf")

    def test_multiple_images_use_converted(self):
        self.assertEqual(default_output_name([Path("a.png"), Path("b.jpg")]), "converted.pdf")

    def test_custom_name_gets_pdf_extension(self):
        out = resolve_output_path([Path("a.png")], output_name="final")
        self.assertEqual(out, Path("final.pdf"))

    def test_custom_name_with_extension_is_kept(self):
        out = resolve_output_path([Path("a.png")], output_name="final_document.pdf")
        self.assertEqual(out, Path("final_document.pdf"))

    def test_output_dir_is_applied(self):
        out = resolve_output_path([Path("abc.png")], output_dir="output/")
        self.assertEqual(out, Path("output") / "abc.pdf")

    def test_name_and_dir_combine(self):
        out = resolve_output_path([Path("a.png")], "r.pdf", "out")
        self.assertEqual(out, Path("out") / "r.pdf")

    def test_blank_name_or_dir_rejected(self):
        with self.assertRaises(OutputPathError):
            resolve_output_path([Path("a.png")], output_name="   ")
        with self.assertRaises(OutputPathError):
            resolve_output_path([Path("a.png")], output_dir="  ")

    def test_extension_check(self):
        self.assertTrue(has_supported_extension(Path("x.JPEG")))
        self.assertFalse(has_supported_extension(Path("x.gif")))


class PrepareOutputTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_missing_directory(self):
        target = self.tmp / "new" / "deep" / "a.pdf"
        prepare_output_path(target)
        self.assertTrue(target.parent.is_dir())

    def test_existing_file_blocked_without_overwrite(self):
        target = self.tmp / "a.pdf"
        target.write_bytes(b"old")
        with self.assertRaises(OutputExistsError):
            prepare_output_path(target, overwrite=False)
        self.assertEqual(target.read_bytes(), b"old")

    def test_existing_file_allowed_with_overwrite(self):
        target = self.tmp / "a.pdf"
        target.write_bytes(b"old")
        self.assertEqual(prepare_output_path(target, overwrite=True), target)

    def test_directory_as_output_rejected(self):
        folder = self.tmp / "x.pdf"
        folder.mkdir()
        with self.assertRaises(OutputPathError):
            prepare_output_path(folder, overwrite=True)

    def test_parent_that_is_a_file_rejected(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("x")
        with self.assertRaises(OutputPathError):
            prepare_output_path(blocker / "a.pdf")

    def test_output_cannot_be_an_input(self):
        src = self.tmp / "a.pdf"
        src.write_text("x")
        with self.assertRaises(OutputPathError):
            ensure_not_input(src, [src])


if __name__ == "__main__":
    unittest.main()
