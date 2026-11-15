"""PDF creation: lays images out on pages and writes the PDF with Pillow."""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from utils import OutputPathError

logger = logging.getLogger(__name__)

#: Page resolution used for layout and for the PDF itself.
DPI = 300
#: A4 portrait page at 300 DPI, in pixels (210 x 297 mm).
A4_PORTRAIT = (2480, 3508)
#: White margin around each image, in pixels (about 6 mm).
MARGIN_PX = 90
#: JPEG quality used when Pillow embeds the page images.
JPEG_QUALITY = 95


def page_size_for(image: Image.Image) -> Tuple[int, int]:
    """Return the A4 page size (portrait or landscape) that suits ``image``."""
    width, height = image.size
    if width > height:
        return (A4_PORTRAIT[1], A4_PORTRAIT[0])  # landscape
    return A4_PORTRAIT


def fit_to_page(image: Image.Image) -> Image.Image:
    """Place ``image`` centred on a white A4 page.

    The image is scaled (aspect ratio preserved, never stretched) to fill the
    printable area. Landscape images get a landscape page, portrait and square
    images a portrait page.
    """
    page_w, page_h = page_size_for(image)
    avail_w = page_w - 2 * MARGIN_PX
    avail_h = page_h - 2 * MARGIN_PX

    scale = min(avail_w / image.width, avail_h / image.height)
    new_w = max(1, round(image.width * scale))
    new_h = max(1, round(image.height * scale))

    resized = image if (new_w, new_h) == image.size else image.resize(
        (new_w, new_h), Image.Resampling.LANCZOS
    )

    page = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    page.paste(resized, ((page_w - new_w) // 2, (page_h - new_h) // 2))
    return page


def generate_pdf(images: List[Image.Image], output_path: Path) -> Path:
    """Write ``images`` (one per page) to a PDF file.

    Args:
        images: RGB images, in page order. Must not be empty.
        output_path: Destination ``.pdf`` path (directory must already exist).

    Returns:
        ``output_path`` on success.

    Raises:
        ValueError: If ``images`` is empty.
        OutputPathError: If the file cannot be written.
    """
    if not images:
        raise ValueError("No images supplied for PDF generation.")

    pages = [fit_to_page(img) for img in images]
    first, rest = pages[0], pages[1:]
    logger.debug("Writing %d page(s) to %s", len(pages), output_path)

    # Write to a temporary file first so a failure can never destroy an
    # existing PDF (or leave a half-written one behind).
    temp_path = output_path.with_name(output_path.name + ".tmp")
    try:
        first.save(
            temp_path,
            "PDF",
            resolution=float(DPI),
            quality=JPEG_QUALITY,
            save_all=True,
            append_images=rest,
        )
        os.replace(temp_path, output_path)
    except PermissionError:
        _remove_temp(temp_path)
        raise OutputPathError(f"Permission denied: cannot write '{output_path}'.")
    except OSError as exc:
        _remove_temp(temp_path)
        raise OutputPathError(f"Could not write '{output_path}': {exc.strerror or exc}.")
    return output_path


def _remove_temp(path: Path) -> None:
    """Delete the temporary file created during PDF generation."""
    try:
        path.unlink()
    except OSError:
        pass
