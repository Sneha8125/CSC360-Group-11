"""Image validation, loading and preprocessing (Pillow based).

The source files are only ever opened for reading; they are never modified.
"""

import logging
import warnings
from pathlib import Path
from typing import List

from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError

from utils import CorruptImageError, InputFileError, validate_input_path

logger = logging.getLogger(__name__)

#: Colour used to flatten transparent areas (PDF pages have no alpha channel).
BACKGROUND_COLOR = (255, 255, 255)


def validate_image(path: str) -> Path:
    """Fully validate an input image.

    Checks existence, extension, and that Pillow can really decode the pixel
    data (this catches truncated / corrupted files, not just bad headers).

    Returns:
        The validated path.

    Raises:
        InputFileError, UnsupportedFormatError: see :func:`utils.validate_input_path`.
        CorruptImageError: If the image is damaged or unreadable.
    """
    file_path = validate_input_path(path)

    try:
        # Pillow turns "decompression bomb" warnings into errors when asked to.
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            # First pass: verify() checks the file structure.
            with Image.open(file_path) as img:
                img.verify()
            # verify() does not decode pixels, so decode in a second pass.
            with Image.open(file_path) as img:
                for frame in ImageSequence.Iterator(img):
                    frame.load()
    except (UnidentifiedImageError, SyntaxError, ValueError, EOFError) as exc:
        raise CorruptImageError(
            f"File '{path}' is corrupted or is not a valid image ({exc})."
        )
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise CorruptImageError(f"Image '{path}' is too large to process safely.")
    except PermissionError:
        raise InputFileError(f"Permission denied: cannot read '{path}'.")
    except OSError as exc:  # truncated files raise OSError
        raise CorruptImageError(f"File '{path}' is corrupted or unreadable ({exc}).")

    logger.debug("Validated image: %s", file_path)
    return file_path


def to_rgb(image: Image.Image) -> Image.Image:
    """Convert any Pillow image to plain RGB, flattening transparency on white."""
    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    if has_alpha:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, BACKGROUND_COLOR)
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    if image.mode in ("I;16", "I;16L", "I;16B", "I"):
        # 16-bit greyscale: scale down to 8 bit before converting.
        image = image.point(lambda v: v / 256).convert("L")
    return image.convert("RGB")


def load_images(path: str) -> List[Image.Image]:
    """Open an image and return its pages as RGB images.

    Multi-page TIFFs yield one image per frame; every other format yields one.
    EXIF orientation is applied so photos appear upright.

    Raises:
        CorruptImageError: If decoding fails.
    """
    file_path = validate_image(path)
    pages: List[Image.Image] = []
    try:
        with Image.open(file_path) as img:
            for frame in ImageSequence.Iterator(img):
                frame.load()
                upright = ImageOps.exif_transpose(frame)
                pages.append(to_rgb(upright))
    except (OSError, ValueError, SyntaxError, EOFError) as exc:
        raise CorruptImageError(f"File '{path}' could not be processed ({exc}).")

    if not pages:
        raise CorruptImageError(f"File '{path}' contains no image data.")
    logger.debug("Loaded %d page(s) from %s", len(pages), file_path)
    return pages
