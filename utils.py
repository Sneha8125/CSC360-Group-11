"""Utility helpers: exceptions, path validation and output-path resolution.

Everything in this module deals with the file system only; no image or PDF
processing happens here.
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

#: Image extensions accepted by the converter (lower-case, with leading dot).
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

#: File name used when several images are merged and no -o is given.
DEFAULT_MULTI_OUTPUT_NAME = "converted.pdf"


# --------------------------------------------------------------------------
# Exceptions
# --------------------------------------------------------------------------
class ConverterError(Exception):
    """Base class for all user-facing errors raised by the application."""


class InputFileError(ConverterError):
    """The input file is missing, is not a file, or cannot be read."""


class UnsupportedFormatError(ConverterError):
    """The input file does not have a supported image format."""


class CorruptImageError(ConverterError):
    """The input file is damaged or is not a valid image."""


class OutputPathError(ConverterError):
    """The requested output location is invalid or not writable."""


class OutputExistsError(OutputPathError):
    """The output PDF already exists and overwriting was not requested."""


# --------------------------------------------------------------------------
# Input helpers
# --------------------------------------------------------------------------
def supported_formats_text() -> str:
    """Return the supported formats as a readable string (e.g. ``PNG, JPG``)."""
    return ", ".join(ext.lstrip(".").upper() for ext in SUPPORTED_EXTENSIONS)


def has_supported_extension(path: Path) -> bool:
    """Return True if ``path`` has one of the supported image extensions."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def validate_input_path(path: str) -> Path:
    """Check that ``path`` exists, is a readable file and has a supported extension.

    Args:
        path: Path string supplied on the command line.

    Returns:
        The path as a :class:`pathlib.Path`.

    Raises:
        InputFileError: If the file is missing, is a directory or is unreadable.
        UnsupportedFormatError: If the extension is not supported.
    """
    if path is None or not str(path).strip():
        raise InputFileError("Empty file path supplied.")

    file_path = Path(path).expanduser()

    if not file_path.exists():
        raise InputFileError(f"File '{path}' does not exist.")
    if not file_path.is_file():
        raise InputFileError(f"'{path}' is not a file.")
    if not has_supported_extension(file_path):
        raise UnsupportedFormatError(
            f"File '{path}' has an unsupported format "
            f"(supported: {supported_formats_text()})."
        )
    try:
        with open(file_path, "rb"):
            pass
    except PermissionError:
        raise InputFileError(f"Permission denied: cannot read '{path}'.")
    except OSError as exc:
        raise InputFileError(f"Cannot read '{path}': {exc.strerror or exc}.")

    return file_path


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------
def default_output_name(inputs: List[Path]) -> str:
    """Return the default PDF file name for the given input files.

    A single image keeps its own name (``abc.png`` -> ``abc.pdf``); several
    images are merged into ``converted.pdf``.
    """
    if len(inputs) == 1:
        return inputs[0].stem + ".pdf"
    return DEFAULT_MULTI_OUTPUT_NAME


def resolve_output_path(
    inputs: List[Path],
    output_name: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Path:
    """Work out the final PDF path from the CLI options.

    Args:
        inputs: Validated input image paths.
        output_name: Value of ``-o`` (may be ``None``). ``.pdf`` is appended
            if missing.
        output_dir: Value of ``-d`` (may be ``None`` for the current directory).

    Raises:
        OutputPathError: If the name or directory is invalid.
    """
    name = output_name if output_name else default_output_name(inputs)

    if not str(name).strip():
        raise OutputPathError("Output file name must not be empty.")

    name_path = Path(name).expanduser()
    if name_path.name in ("", ".", ".."):
        raise OutputPathError(f"Invalid output file name '{name}'.")
    if name_path.suffix.lower() != ".pdf":
        name_path = name_path.with_name(name_path.name + ".pdf")

    if output_dir is not None:
        if not str(output_dir).strip():
            raise OutputPathError("Output directory must not be empty.")
        # A relative -o is placed inside the -d directory.
        return Path(output_dir).expanduser() / name_path
    return name_path


def prepare_output_path(output_path: Path, overwrite: bool = False) -> Path:
    """Create the output directory if needed and guard against overwriting.

    Raises:
        OutputExistsError: If the file exists and ``overwrite`` is False.
        OutputPathError: If the directory/path is invalid or not writable.
    """
    if output_path.exists():
        if output_path.is_dir():
            raise OutputPathError(f"'{output_path}' is a directory, not a file.")
        if not overwrite:
            raise OutputExistsError(
                f"Output file '{output_path}' already exists. "
                "Use --overwrite to replace it."
            )

    parent = output_path.parent
    if parent.exists() and not parent.is_dir():
        raise OutputPathError(f"'{parent}' exists but is not a directory.")

    try:
        parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise OutputPathError(f"Permission denied: cannot create directory '{parent}'.")
    except OSError as exc:
        raise OutputPathError(f"Invalid output directory '{parent}': {exc.strerror or exc}.")

    return output_path


def ensure_not_input(output_path: Path, inputs: List[Path]) -> None:
    """Make sure the PDF can never replace one of the source images."""
    try:
        resolved_out = output_path.resolve()
        for src in inputs:
            if src.resolve() == resolved_out:
                raise OutputPathError(
                    f"Output path '{output_path}' would overwrite the input file."
                )
    except OSError:
        # Resolution problems are reported later when the file is written.
        pass
