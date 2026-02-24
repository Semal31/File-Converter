"""Converter package — format detection, routing, and dispatch.

All public surface:
    detect_format(filename, mime_type?) → (canonical_format, category)
    get_available_formats(fmt, category) → [output_format, ...]
    convert_file(input_path, input_format, output_format, category, output_path) → None
"""

from pathlib import Path

from .archives import ArchiveConverter
from .audio import AudioConverter
from .data import DataConverter
from .documents import DocumentConverter
from .images import ImageConverter
from .video import VideoConverter

# ── Converter registry ────────────────────────────────────────────────────────

_CONVERTERS: dict[str, object] = {
    "document": DocumentConverter(),
    "image": ImageConverter(),
    "audio": AudioConverter(),
    "video": VideoConverter(),
    "data": DataConverter(),
    "archive": ArchiveConverter(),
}

# ── Extension lookup table ────────────────────────────────────────────────────
# Maps lowercase extension (without dot) → (canonical_format, category)
_EXT_MAP: dict[str, tuple[str, str]] = {}

for _cat, _conv in _CONVERTERS.items():
    for _fmt in _conv.supported_formats:  # type: ignore[union-attr]
        for _ext in _conv.format_extensions(_fmt):  # type: ignore[union-attr]
            _EXT_MAP[_ext] = (_fmt, _cat)

# ── Public API ────────────────────────────────────────────────────────────────


def detect_format(filename: str, mime_type: str | None = None) -> tuple[str, str]:
    """Return (canonical_format, category) for *filename*.

    Raises:
        ValueError: if the file extension is not recognised.
    """
    name = filename.lower()

    # Handle compound extensions first
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return ("tar.gz", "archive")
    if name.endswith(".tar.bz2"):
        raise ValueError("tar.bz2 is not supported; please use tar.gz or zip.")

    ext = Path(name).suffix.lstrip(".")
    if not ext:
        raise ValueError(f"Cannot determine format: '{filename}' has no file extension.")

    entry = _EXT_MAP.get(ext)
    if entry is None:
        raise ValueError(f"'.{ext}' is not a supported format.")
    return entry


def get_available_formats(fmt: str, category: str) -> list[str]:
    """Return the list of output formats this input format can be converted to."""
    conv = _CONVERTERS.get(category)
    if conv is None:
        return []
    return conv.get_output_formats(fmt)  # type: ignore[union-attr]


async def convert_file(
    input_path: Path,
    input_format: str,
    output_format: str,
    category: str,
    output_path: Path,
    **kwargs,
) -> None:
    """Dispatch conversion to the appropriate converter module.

    Any extra kwargs (e.g. quality="high") are forwarded to the converter and
    silently ignored by converters that don't use them.
    """
    conv = _CONVERTERS.get(category)
    if conv is None:
        raise ValueError(f"No converter registered for category '{category}'.")
    await conv.convert(input_path, input_format, output_format, output_path, **kwargs)  # type: ignore[union-attr]
