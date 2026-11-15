
"""PDF creation: lays images out on pages and writes the PDF with Pillow."""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from PIL import Image

from utils import OutputPathError

logger = logging.getLogger(__name__)

DPI = 300

# Page dimensions in pixels at 300 DPI.
# Values represent portrait orientation: width, height.
A4_PORTRAIT = (2480, 3508)

PAGE_SIZES = {
    "A4": A4_PORTRAIT,
    "A3": (3508, 4961),
    "LETTER": (2550, 3300),
    "LEGAL": (2550, 4200),
}

MARGIN_PX = 90
JPEG_QUALITY = 95


def page_size_for(
    image: Image.Image,
    page_size: str = "A4",
) -> Tuple[int, int]:
    """Return the selected page size in portrait or landscape orientation."""
    page_size = page_size.upper()

    if page_size not in PAGE_SIZES:
        raise ValueError(
            f"Unsupported page size '{page_size}'. "
            f"Choose from: {', '.join(PAGE_SIZES)}."
        )

    width, height = PAGE_SIZES[page_size]

    if image.width > image.height:
        return height, width

    return width, height


def fit_to_page(
    image: Image.Image,
    page_size: str = "A4",
) -> Image.Image:
    """Scale and centre an image on the selected PDF page size."""
    page_w, page_h = page_size_for(image, page_size)

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


def generate_pdf(
    images: List[Image.Image],
    output_path: Path,
    page_size: str = "A4",
) -> Path:
    """Generate a PDF using the selected page size."""
    if not images:
        raise ValueError("No images supplied for PDF generation.")

    pages = [fit_to_page(img, page_size) for img in images]

    first, rest = pages[0], pages[1:]

    logger.debug(
        "Writing %d page(s) to %s using %s page size",
        len(pages),
        output_path,
        page_size,
    )

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
        raise OutputPathError(
            f"Permission denied: cannot write '{output_path}'."
        )

    except OSError as exc:
        _remove_temp(temp_path)
        raise OutputPathError(
            f"Could not write '{output_path}': {exc.strerror or exc}."
        )

    return output_path


def _remove_temp(path: Path) -> None:
    """Remove a temporary PDF file after a failed operation."""
    try:
        path.unlink()
    except OSError:
        pass
