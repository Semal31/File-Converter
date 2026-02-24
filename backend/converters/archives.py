"""Archive format converter.

Supports: ZIP, TAR, TAR.GZ, 7Z
Strategy: extract the source archive to a temp directory, repack into the target format.
"""

import asyncio
import functools
import logging
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.archives")

_EXTENSIONS: dict[str, list[str]] = {
    "zip": ["zip"],
    "tar": ["tar"],
    "tar.gz": ["tar.gz", "tgz"],
    "7z": ["7z"],
}

_ALL = list(_EXTENSIONS.keys())


class ArchiveConverter(BaseConverter):
    """Repack archive files from one format to another."""

    @property
    def supported_formats(self) -> list[str]:
        return _ALL

    def format_extensions(self, fmt: str) -> list[str]:
        return _EXTENSIONS.get(fmt, [])

    def get_output_formats(self, input_format: str) -> list[str]:
        return [f for f in _ALL if f != input_format]

    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        # quality kwarg is not applicable to archive repacking; ignored.
        progress_callback = kwargs.get("progress_callback", None)
        fn = functools.partial(
            self._convert_sync, input_path, input_format, output_format, output_path,
            progress_callback=progress_callback,
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, fn)

    def _convert_sync(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        progress_callback=None,
        **kwargs,  # quality and other kwargs not applicable to this converter type
    ) -> None:
        if progress_callback:
            progress_callback(50)
        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            self._extract(input_path, input_format, extract_dir)
            self._pack(extract_dir, output_format, output_path)
        if progress_callback:
            progress_callback(99)
        log.info("archive: %s → %s OK", input_format, output_format)

    # ── Extractors ───────────────────────────────────────────────────────────

    def _extract(self, path: Path, fmt: str, dest: Path) -> None:
        if fmt == "zip":
            with zipfile.ZipFile(path, "r") as zf:
                for member in zf.namelist():
                    member_path = (dest / member).resolve()
                    if not str(member_path).startswith(str(dest.resolve())):
                        raise ValueError(f"Zip entry '{member}' would escape extraction directory")
                zf.extractall(dest)
        elif fmt == "tar":
            with tarfile.open(path, "r:") as tf:
                tf.extractall(dest, filter="data")
        elif fmt == "tar.gz":
            with tarfile.open(path, "r:gz") as tf:
                tf.extractall(dest, filter="data")
        elif fmt == "7z":
            import py7zr  # type: ignore

            with py7zr.SevenZipFile(path, "r") as sz:
                sz.extractall(dest)
        else:
            raise ValueError(f"Cannot extract from format: {fmt!r}")

    # ── Packers ──────────────────────────────────────────────────────────────

    def _pack(self, src_dir: Path, fmt: str, dest: Path) -> None:
        files = list(src_dir.rglob("*"))

        if fmt == "zip":
            with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for f in files:
                    if f.is_file():
                        zf.write(f, f.relative_to(src_dir))

        elif fmt == "tar":
            with tarfile.open(dest, "w:") as tf:
                for f in files:
                    if f.is_file():
                        tf.add(f, arcname=f.relative_to(src_dir))

        elif fmt == "tar.gz":
            with tarfile.open(dest, "w:gz", compresslevel=6) as tf:
                for f in files:
                    if f.is_file():
                        tf.add(f, arcname=f.relative_to(src_dir))

        elif fmt == "7z":
            import py7zr  # type: ignore

            with py7zr.SevenZipFile(dest, "w") as sz:
                for f in files:
                    if f.is_file():
                        sz.write(f, f.relative_to(src_dir))
        else:
            raise ValueError(f"Cannot pack to format: {fmt!r}")
