"""Document format converter.

Supports: PDF, DOCX, TXT, Markdown (MD), HTML
Engine: pypandoc (wraps the pandoc binary) + weasyprint for HTML→PDF fallback.
"""

import asyncio
import functools
import logging
import subprocess
import tempfile
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.documents")

# Maps our canonical names → pandoc format strings
_PANDOC_READ: dict[str, str] = {
    "docx": "docx",
    "txt": "plain",
    "md": "markdown",
    "html": "html",
}
_PANDOC_WRITE: dict[str, str] = {
    "docx": "docx",
    "txt": "plain",
    "md": "markdown",
    "html": "html",
}

_EXTENSIONS: dict[str, list[str]] = {
    "pdf": ["pdf"],
    "docx": ["docx"],
    "txt": ["txt"],
    "md": ["md", "markdown"],
    "html": ["html", "htm"],
}


class DocumentConverter(BaseConverter):
    """Convert between document formats using pandoc."""

    @property
    def supported_formats(self) -> list[str]:
        return list(_EXTENSIONS.keys())

    def format_extensions(self, fmt: str) -> list[str]:
        return _EXTENSIONS.get(fmt, [])

    def get_output_formats(self, input_format: str) -> list[str]:
        if input_format == "pdf":
            return []  # pandoc cannot read PDFs
        return [f for f in self.supported_formats if f != input_format]

    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        # quality kwarg is not applicable to document conversion; ignored.
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
        import pypandoc

        if output_format == "pdf":
            if progress_callback:
                progress_callback(50)
            self._to_pdf(input_path, input_format, output_path)
            if progress_callback:
                progress_callback(99)
            return

        in_fmt = _PANDOC_READ.get(input_format)
        out_fmt = _PANDOC_WRITE.get(output_format)

        if in_fmt is None or out_fmt is None:
            raise ValueError(f"No pandoc mapping for {input_format!r} → {output_format!r}")

        extra_args: list[str] = []
        if output_format == "html":
            extra_args = ["--standalone"]

        if progress_callback:
            progress_callback(50)
        pypandoc.convert_file(
            str(input_path),
            out_fmt,
            format=in_fmt,
            outputfile=str(output_path),
            extra_args=extra_args,
        )
        if progress_callback:
            progress_callback(99)
        log.info("pandoc: %s → %s OK", input_format, output_format)

    def _to_pdf(self, input_path: Path, input_format: str, output_path: Path) -> None:
        """Convert any document format to PDF.

        Strategy:
        1. If input is already HTML, feed directly to weasyprint.
        2. Otherwise convert to HTML via pandoc first, then weasyprint.
        """
        import pypandoc

        if input_format == "html":
            html_path = input_path
            tmp = None
        else:
            in_fmt = _PANDOC_READ.get(input_format)
            if in_fmt is None:
                raise ValueError(f"No pandoc mapping for {input_format!r}")
            tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
            tmp.close()
            html_path = Path(tmp.name)
            pypandoc.convert_file(
                str(input_path),
                "html",
                format=in_fmt,
                outputfile=str(html_path),
                extra_args=["--standalone"],
            )

        try:
            self._weasyprint_html_to_pdf(html_path, output_path)
        finally:
            if tmp:
                html_path.unlink(missing_ok=True)

    @staticmethod
    def _weasyprint_html_to_pdf(html_path: Path, output_path: Path) -> None:
        from weasyprint import HTML  # type: ignore

        HTML(filename=str(html_path)).write_pdf(str(output_path))
        log.info("weasyprint: HTML → PDF OK")
