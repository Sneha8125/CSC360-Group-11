"""Shared helpers for the test-suite (path setup and sample-image factories)."""

import sys
from pathlib import Path

from PIL import Image

# Make the project root importable when tests run from any directory.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_image(path: Path, size=(200, 120), mode="RGB", color=(30, 120, 200)) -> Path:
    """Create a small image file; format is chosen from the file extension."""
    img = Image.new(mode, size, color)
    img.save(path)
    return path


def pdf_page_count(path: Path) -> int:
    """Return the page count by counting page objects in the raw PDF bytes."""
    data = Path(path).read_bytes()
    return data.count(b"/Type /Page\n") + data.count(b"/Type /Page ") + data.count(
        b"/Type /Page/"
    ) + data.count(b"/Type /Page>")
