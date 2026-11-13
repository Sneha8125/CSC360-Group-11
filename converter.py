#!/usr/bin/env python3
"""Image to PDF Converter - command line entry point.

Usage examples::

    python converter.py abc.png
    python converter.py a.png b.jpg c.jpeg
    python converter.py abc.png -o final_document.pdf
    python converter.py abc.png -d output/
    python converter.py abc.png --overwrite
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from image_processor import load_images, validate_image
from pdf_generator import generate_pdf
from utils import (
    ConverterError,
    ensure_not_input,
    prepare_output_path,
    resolve_output_path,
    supported_formats_text,
)

logger = logging.getLogger("converter")

BANNER_WIDTH = 36


def build_parser() -> argparse.ArgumentParser:
    """Create the argparse command-line parser."""
    parser = argparse.ArgumentParser(
        prog="converter.py",
        description="Convert one or more images into a single PDF document.",
        epilog=(
            f"Supported formats: {supported_formats_text()}.\n"
            "Original image files are never modified or deleted."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "images",
        nargs="*",
        metavar="IMAGE",
        help="one or more image files; several images are combined into one PDF",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="NAME",
        help="output PDF file name (default: <image name>.pdf, or converted.pdf "
             "for several images)",
    )
    parser.add_argument(
        "-d", "--output-dir",
        metavar="DIR",
        help="directory to save the PDF in (created if missing; default: current directory)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing an existing PDF",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="show detailed log messages",
    )
    return parser


def configure_logging(verbose: bool) -> None:
    """Send log output to stderr; DEBUG when verbose, otherwise only errors."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.CRITICAL,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def print_banner() -> None:
    """Print the application banner."""
    line = "=" * BANNER_WIDTH
    print(line)
    print("IMAGE TO PDF CONVERTER".center(BANNER_WIDTH).rstrip())
    print(line)
    print()


def print_success(inputs: List[Path], output: Path, raw_inputs: List[str]) -> None:
    """Print the success report in the format required by the specification."""
    print_banner()
    if len(inputs) == 1:
        print(f"Input File  : {raw_inputs[0]}")
        print(f"Output File : {output}")
        print("Status      : Conversion Successful!")
        print()
        print("PDF generated successfully.")
    else:
        print(f"{len(inputs)} images processed successfully.")
        print(f"Output PDF: {output}")


def convert(
    image_args: List[str],
    output_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    overwrite: bool = False,
) -> Path:
    """Run the full conversion pipeline and return the created PDF path.

    Raises:
        ConverterError: For any user-facing problem (bad input, bad output...).
    """
    if not image_args:
        raise ConverterError("No input images supplied. Run with --help for usage.")

    # 1. Validate every input first so nothing is written if any file is bad.
    inputs = [validate_image(arg) for arg in image_args]

    # 2. Work out and check the output location.
    output_path = resolve_output_path(inputs, output_name, output_dir)
    ensure_not_input(output_path, inputs)
    prepare_output_path(output_path, overwrite)

    # 3. Load, lay out and write.
    pages = []
    for arg in image_args:
        pages.extend(load_images(arg))
    generate_pdf(pages, output_path)
    logger.debug("Created %s from %d image file(s)", output_path, len(inputs))
    return output_path


def main(argv: Optional[List[str]] = None) -> int:
    """Program entry point. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        output = convert(args.images, args.output, args.output_dir, args.overwrite)
    except ConverterError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130

    inputs = [Path(p) for p in args.images]
    print_success(inputs, output, args.images)
    return 0


if __name__ == "__main__":
    sys.exit(main())
