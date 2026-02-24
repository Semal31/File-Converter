"""Video format converter.

Supports: MP4, MKV, AVI, WEBM, MOV, GIF
Engine: ffmpeg CLI via ffmpeg-progress-yield for video; subprocess for GIF two-pass.

Quality levels (passed via convert(..., quality="original")):
    high     — CRF 15 for x264/mpeg4, CRF 20 for VP9  (near-transparent quality)
    original — CRF 18 for x264/mpeg4, CRF 24 for VP9  (default; best reasonable trade-off)
    medium   — CRF 23 for x264/mpeg4, CRF 30 for VP9  (smaller file, still good)
    low      — CRF 28 for x264/mpeg4, CRF 35 for VP9  (smallest file)

GIF-specific parameters (passed as kwargs):
    max_width (int | None): cap output width in pixels; None = use source resolution (default)
"""

import asyncio
import functools
import logging
import subprocess
import tempfile
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.video")

# ── Format metadata ───────────────────────────────────────────────────────────

_EXTENSIONS: dict[str, list[str]] = {
    "mp4":  ["mp4"],
    "mkv":  ["mkv"],
    "avi":  ["avi"],
    "webm": ["webm"],
    "mov":  ["mov"],
    "gif":  ["gif"],
}

_VIDEO_CODEC: dict[str, str] = {
    "mp4":  "libx264",
    "mkv":  "libx264",
    "avi":  "mpeg4",
    "webm": "libvpx-vp9",
    "mov":  "libx264",
    "gif":  "gif",
}

_AUDIO_CODEC: dict[str, str | None] = {
    "mp4":  "aac",
    "mkv":  "aac",
    "avi":  "mp3",
    "webm": "libvorbis",
    "mov":  "aac",
    "gif":  None,  # GIF carries no audio track
}

# CRF values per quality level: (x264/mpeg4 crf, vp9 crf)
# Lower CRF = higher quality. 0 = lossless for x264.
_CRF: dict[str, tuple[int, int]] = {
    "lossless": (0,  0),   # CRF 0 = mathematically lossless for x264 and VP9
    "high":     (15, 20),
    "original": (18, 24),  # default — best reasonable trade-off, no bitrate-matching for video
    "medium":   (23, 30),
    "low":      (28, 35),
}

# ── Source probe ──────────────────────────────────────────────────────────────


def _probe_video(path: Path) -> dict:
    """Return {width, height, fps} for the first video stream via ffprobe.

    Returns safe defaults on failure so callers never need to guard against None.
    """
    try:
        import ffmpeg  # type: ignore

        probe = ffmpeg.probe(str(path))
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                w = int(stream.get("width",  0))
                h = int(stream.get("height", 0))
                fps_str = stream.get("r_frame_rate", "24/1")
                try:
                    num, den = fps_str.split("/")
                    fps = float(num) / max(1.0, float(den))
                except (ValueError, ZeroDivisionError):
                    fps = 24.0
                return {"width": w, "height": h, "fps": fps}
    except Exception as exc:
        log.debug("ffprobe failed for %s: %s", path.name, exc)

    return {"width": 0, "height": 0, "fps": 24.0}


# ── Converter ─────────────────────────────────────────────────────────────────


class VideoConverter(BaseConverter):
    """Convert between video and animation formats using ffmpeg."""

    @property
    def supported_formats(self) -> list[str]:
        return list(_EXTENSIONS.keys())

    def format_extensions(self, fmt: str) -> list[str]:
        return _EXTENSIONS.get(fmt, [])

    def get_output_formats(self, input_format: str) -> list[str]:
        return [f for f in self.supported_formats if f != input_format]

    async def convert(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        **kwargs,
    ) -> None:
        quality:           str        = kwargs.get("quality",           "original")
        max_width:         int | None = kwargs.get("max_width",         None)
        progress_callback             = kwargs.get("progress_callback", None)
        fn = functools.partial(
            self._convert_sync,
            input_path, input_format, output_format, output_path,
            quality=quality, max_width=max_width, progress_callback=progress_callback,
        )
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, fn)

    def _convert_sync(
        self,
        input_path: Path,
        input_format: str,
        output_format: str,
        output_path: Path,
        quality: str = "original",
        max_width: int | None = None,
        progress_callback=None,
    ) -> None:
        if output_format == "gif":
            self._to_gif(input_path, output_path, max_width=max_width,
                         progress_callback=progress_callback)
            return

        from ffmpeg_progress_yield import FfmpegProgress  # type: ignore

        vcodec = _VIDEO_CODEC.get(output_format, "libx264")
        acodec = _AUDIO_CODEC.get(output_format)
        crf_x264, crf_vp9 = _CRF.get(quality, _CRF["original"])

        # Build the ffmpeg CLI args list
        cmd: list[str] = [
            "ffmpeg",
            "-i", str(input_path),
            "-vcodec", vcodec,
            "-loglevel", "error",
        ]

        if acodec is not None:
            cmd += ["-acodec", acodec]

        if vcodec in ("libx264", "mpeg4"):
            cmd += ["-crf", str(crf_x264), "-preset", "medium"]
        elif vcodec == "libvpx-vp9":
            cmd += ["-crf", str(crf_vp9), "-b:v", "0"]

        cmd += [str(output_path), "-y"]

        with FfmpegProgress(cmd) as ff:
            for pct in ff.run_command_with_progress():
                if progress_callback:
                    progress_callback(pct)

        active_crf = crf_x264 if vcodec != "libvpx-vp9" else crf_vp9
        log.info(
            "video: %s → %s OK (codec=%s CRF=%d quality=%s)",
            input_format, output_format, vcodec, active_crf, quality,
        )

    @staticmethod
    def _to_gif(
        input_path: Path,
        output_path: Path,
        max_width: int | None = None,
        progress_callback=None,
    ) -> None:
        """Two-pass palette-based GIF encoding.

        Uses source resolution and FPS (capped at 24) by default.
        Pass max_width to downscale proportionally if the source is wider.
        Reports stage-based progress: 30 after palette generation, 99 after encode.
        """
        info      = _probe_video(input_path)
        src_fps   = info["fps"]   if info["fps"]   > 0 else 24.0
        src_width = info["width"] if info["width"] > 0 else 0

        # Cap at 24 fps — higher rates balloon file size with minimal perceptual gain
        gif_fps = min(src_fps, 24.0)

        # scale_w:
        #   -2       = keep source width, ensure even pixel count (GIF requires it)
        #   max_width = downscale to this width when source is wider
        if max_width and src_width > max_width:
            scale_w = str(max_width)
        else:
            scale_w = "-2"

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            palette_path = tmp.name

        try:
            # Pass 1 — build an optimised per-content colour palette.
            # "diff" stats_mode weights colours by motion, giving far better
            # results for animated content than the default full-frame analysis.
            pass1_cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-vf", f"fps={gif_fps},scale={scale_w}:-2:flags=lanczos,palettegen=stats_mode=diff",
                "-loglevel", "error",
                "-y", palette_path,
            ]
            subprocess.run(pass1_cmd, check=True)

            if progress_callback:
                progress_callback(30)

            # Pass 2 — encode using the generated palette.
            pass2_cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-i", palette_path,
                "-lavfi", f"fps={gif_fps},scale={scale_w}:-2:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer",
                "-loglevel", "error",
                "-y", str(output_path),
            ]
            subprocess.run(pass2_cmd, check=True)

            if progress_callback:
                progress_callback(99)

        finally:
            Path(palette_path).unlink(missing_ok=True)

        width_label = f"{max_width}px" if (max_width and src_width > max_width) else "source"
        log.info(
            "video: → GIF OK (fps=%.1f width=%s palette-method)",
            gif_fps, width_label,
        )
