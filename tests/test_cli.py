
"""End-to-end tests for the command-line interface."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from tests.helpers import make_image, pdf_page_count
import converter


class CliTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._cwd = os.getcwd()

        os.chdir(self.tmp)

        make_image(self.tmp / "abc.png")
        make_image(self.tmp / "b.jpg")
        make_image(self.tmp / "c.jpeg")

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def run_cli(self, *argv):
        out = io.StringIO()
        err = io.StringIO()

        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = converter.main(list(argv))

        return code, out.getvalue(), err.getvalue()

    def test_single_image(self):
        code, out, _ = self.run_cli("abc.png")

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "abc.pdf").is_file())
        self.assertIn("Status      : Conversion Successful!", out)
        self.assertIn("PDF generated successfully.", out)

    def test_multiple_images_are_combined(self):
        code, out, _ = self.run_cli("abc.png", "b.jpg", "c.jpeg")

        self.assertEqual(code, 0)
        self.assertEqual(pdf_page_count(self.tmp / "converted.pdf"), 3)
        self.assertIn("3 images processed successfully.", out)
        self.assertIn("Output PDF: converted.pdf", out)

    def test_custom_output_name(self):
        code, _, _ = self.run_cli("abc.png", "-o", "final_document.pdf")

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "final_document.pdf").is_file())

    def test_custom_output_directory(self):
        code, _, _ = self.run_cli("abc.png", "-d", "output/")

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "output" / "abc.pdf").is_file())

    def test_existing_pdf_not_overwritten_by_default(self):
        (self.tmp / "abc.pdf").write_bytes(b"precious")

        code, _, err = self.run_cli("abc.png")

        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        self.assertEqual((self.tmp / "abc.pdf").read_bytes(), b"precious")

    def test_overwrite_flag(self):
        (self.tmp / "abc.pdf").write_bytes(b"old")

        code, _, _ = self.run_cli("abc.png", "--overwrite")

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "abc.pdf").read_bytes().startswith(b"%PDF"))

    def test_missing_file_message(self):
        code, _, err = self.run_cli("ghost.png")

        self.assertEqual(code, 1)
        self.assertIn("Error: File 'ghost.png' does not exist.", err)

    def test_unsupported_format_message(self):
        (self.tmp / "doc.txt").write_text("hi")

        code, _, err = self.run_cli("doc.txt")

        self.assertEqual(code, 1)
        self.assertIn("unsupported format", err)

    def test_corrupted_image_message(self):
        (self.tmp / "bad.png").write_bytes(b"garbage")

        code, _, err = self.run_cli("bad.png")

        self.assertEqual(code, 1)
        self.assertIn("corrupted", err)

    def test_no_pdf_created_when_one_input_is_bad(self):
        code, _, _ = self.run_cli("abc.png", "ghost.png")

        self.assertEqual(code, 1)
        self.assertFalse((self.tmp / "converted.pdf").exists())

    def test_no_arguments(self):
        code, _, err = self.run_cli()

        self.assertEqual(code, 1)
        self.assertIn("No input images", err)

    def test_inputs_are_never_modified(self):
        before = (self.tmp / "abc.png").read_bytes()

        self.run_cli("abc.png")

        self.assertEqual((self.tmp / "abc.png").read_bytes(), before)

    def test_help_exits_cleanly(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                converter.main(["--help"])

        self.assertEqual(ctx.exception.code, 0)

    # New page-size CLI tests

    def test_custom_page_size_a3(self):
        code, _, _ = self.run_cli(
            "abc.png",
            "--page-size",
            "A3",
        )

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "abc.pdf").is_file())

    def test_custom_page_size_letter(self):
        code, _, _ = self.run_cli(
            "abc.png",
            "--page-size",
            "LETTER",
        )

        self.assertEqual(code, 0)
        self.assertTrue((self.tmp / "abc.pdf").is_file())

    def test_invalid_page_size(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli("abc.png", "--page-size", "INVALID")

        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
