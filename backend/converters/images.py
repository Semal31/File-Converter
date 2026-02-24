"""Image format converter.

Supports: PNG, JPG/JPEG, WEBP, BMP, GIF, TIFF/TIF, ICO, SVG (input only → raster)
Engines: Pillow for raster↔raster, cairosvg for SVG→raster.
Note: raster→SVG is not supported (requires tracing software).
"""

import asyncio
import functools
import io
import logging
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.images")

_EXTENSIONS: dict[str, list[str]] = {
    "png": ["png"],
    "jpg": ["jpg", "jpeg"],
    "webp": ["webp"],
    "bmp": ["bmp"],
    "gif": ["gif"],
    "tiff": ["tiff", "tif"],
    "ico": ["ico"],
    "svg": ["svg"],
}

# Pillow save format strings
_PILLOW_SAVE: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
    "ico": "ICO",
}

# SVG can be read but not written by this converter
_SVG_OUTPUTS = [f for f in _EXTENSIONS if f != "svg"]
_RASTER_OUTPUTS = list(_PILLOW_SAVE.keys())


class ImageConverter(BaseConverter):
    """Convert between image formats."""

    @property
    def supported_formats(self) -> list[str]:
        return list(_EXTENSIONS.keys())

    def format_extensions(self, fmt: str) -> list[str]:
        return _EXTENSIONS.get(fmt, [])

    def get_output_formats(self, input_format: str) -> list[str]:
        if input_format == "svg":
            return _SVG_OUTPUTS
        # Raster → raster (no SVG output)
        return [f for f in _RASTER_OUTPUTS if f != input_format]

    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        # quality kwarg is not applicable to image conversion; ignored.
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
        from PIL import Image  # type: ignore

        if input_format == "svg":
            img_data = self._svg_to_png_bytes(input_path)
            img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        else:
            img = Image.open(input_path)

        save_fmt = _PILLOW_SAVE.get(output_format)
        if save_fmt is None:
            raise ValueError(f"Cannot write to format: {output_format!r}")

        # JPEG and BMP don't support alpha channel
        if save_fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        if progress_callback:
            progress_callback(50)

        # ICO has size constraints
        if save_fmt == "ICO":
            img = img.convert("RGBA")
            img.save(str(output_path), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        else:
            save_kwargs: dict = {}
            if save_fmt == "JPEG":
                save_kwargs["quality"] = 92
                save_kwargs["optimize"] = True
            elif save_fmt == "PNG":
                save_kwargs["optimize"] = True
            elif save_fmt == "WEBP":
                save_kwargs["quality"] = 90
                save_kwargs["method"] = 6
            img.save(str(output_path), format=save_fmt, **save_kwargs)

        if progress_callback:
            progress_callback(99)
        log.info("image: %s → %s OK", input_format, output_format)

    @staticmethod
    def _svg_to_png_bytes(svg_path: Path) -> bytes:
        import cairosvg  # type: ignore

        return cairosvg.svg2png(url=str(svg_path))
