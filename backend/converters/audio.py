"""Audio format converter.

Supports: MP3, WAV, OGG, FLAC, AAC, M4A
Engine: pydub (requires ffmpeg on PATH).

Quality modes (passed via convert(..., quality="original")):
    original  — detect source bitrate and match it (default)
    high      — 320k MP3 / 256k AAC+M4A / OGG q:a 9
    medium    — 192k MP3 / 192k AAC+M4A / OGG q:a 6
    low       — 128k MP3 / 128k AAC+M4A / OGG q:a 4

For lossless sources (WAV, FLAC) with quality="original", the "high"
preset is used since there is no compressed bitrate to match.
"""

import asyncio
import functools
import logging
from pathlib import Path

from .base import BaseConverter

log = logging.getLogger("fc.audio")

# ── Format metadata ───────────────────────────────────────────────────────────

_EXTENSIONS: dict[str, list[str]] = {
    "mp3":  ["mp3"],
    "wav":  ["wav"],
    "ogg":  ["ogg"],
    "flac": ["flac"],
    "aac":  ["aac"],
    "m4a":  ["m4a"],
}

# pydub format strings used when *exporting*
_PYDUB_WRITE: dict[str, str] = {
    "mp3":  "mp3",
    "wav":  "wav",
    "ogg":  "ogg",
    "flac": "flac",
    "aac":  "adts",   # raw ADTS bitstream
    "m4a":  "ipod",   # AAC in MPEG-4 container
}

# pydub format hints used when *reading* (avoids mis-detection)
_PYDUB_READ: dict[str, str] = {
    "mp3":  "mp3",
    "wav":  "wav",
    "ogg":  "ogg",
    "flac": "flac",
    "aac":  "aac",
    "m4a":  "m4a",
}

# Formats that are lossless — no meaningful compressed bitrate to preserve
_LOSSLESS = {"wav", "flac"}

# Standard CBR bitrates accepted by the MP3 spec (kbps)
_MP3_STANDARD_KBPS = [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]

# ── Quality presets ───────────────────────────────────────────────────────────
# Each preset defines target bitrates/quality for every lossy output format.

_PRESETS: dict[str, dict] = {
    "high":   {"mp3": "320k", "aac": "256k", "m4a": "256k", "ogg_q": 9},
    "medium": {"mp3": "192k", "aac": "192k", "m4a": "192k", "ogg_q": 6},
    "low":    {"mp3": "128k", "aac": "128k", "m4a": "128k", "ogg_q": 4},
}

# ── Bitrate helpers ───────────────────────────────────────────────────────────


def _probe_bitrate_kbps(path: Path) -> int | None:
    """Return the audio stream bitrate in kbps via ffprobe, or None on failure.

    Tries the per-stream 'bit_rate' field first (most accurate), then falls
    back to the container-level 'bit_rate' (less accurate for multi-stream
    files but useful for single-stream formats like MP3/OGG/FLAC).
    """
    try:
        import ffmpeg  # type: ignore

        probe = ffmpeg.probe(str(path))

        # Prefer the audio stream's own bitrate field
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "audio":
                br = stream.get("bit_rate")
                if br:
                    return max(1, int(br) // 1000)

        # Fallback: container-level bitrate (works well for MP3, AAC, etc.)
        fmt_br = probe.get("format", {}).get("bit_rate")
        if fmt_br:
            return max(1, int(fmt_br) // 1000)

    except Exception as exc:
        log.debug("ffprobe failed for %s: %s", path.name, exc)

    return None


def _mp3_bitrate_for_source(source_kbps: int | None, input_format: str) -> str:
    """Choose an MP3 CBR bitrate string that matches or slightly exceeds source.

    Rules:
    - Lossless source → 320k (best quality, no source to preserve).
    - Unknown source bitrate → 320k (safe default).
    - Lossy source → snap *up* to the nearest standard MP3 bitrate, capped at 320k.
      (Re-encoding lossy→lossy at a *lower* bitrate always loses quality; at the
      same bitrate there is still generational loss, so we stay at or above.)
    """
    if input_format in _LOSSLESS or source_kbps is None:
        return "320k"
    for standard in _MP3_STANDARD_KBPS:
        if standard >= source_kbps:
            return f"{standard}k"
    return "320k"


def _aac_bitrate_for_source(source_kbps: int | None, input_format: str) -> str:
    """Choose an AAC/M4A bitrate string.

    AAC achieves roughly the same perceived quality as MP3 at ~80–85% of the
    bitrate, so we scale accordingly when preserving a lossy source.  For
    lossless or unknown sources we default to 256k.
    """
    if input_format in _LOSSLESS or source_kbps is None:
        return "256k"
    # Scale by 0.85, clamp to [64, 320], round to nearest 8 kbps for clean values
    aac_eq = int(source_kbps * 0.85)
    aac_eq = max(64, min(320, round(aac_eq / 8) * 8))
    return f"{aac_eq}k"


def _ogg_quality_for_source(source_kbps: int | None, input_format: str) -> int:
    """Map source bitrate to an OGG Vorbis quality level (0–10).

    Vorbis quality roughly corresponds to:
      q4 ≈  128 kbps  |  q6 ≈  192 kbps  |  q8 ≈  256 kbps
      q5 ≈  160 kbps  |  q7 ≈  224 kbps  |  q9 ≈  320 kbps
    """
    if input_format in _LOSSLESS or source_kbps is None:
        return 9  # lossless → highest quality Vorbis
    if source_kbps <= 96:  return 4
    if source_kbps <= 128: return 5
    if source_kbps <= 160: return 6
    if source_kbps <= 224: return 7
    if source_kbps <= 256: return 8
    return 9


# ── Converter ─────────────────────────────────────────────────────────────────


class AudioConverter(BaseConverter):
    """Convert between audio formats using pydub + ffmpeg."""

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
        quality: str = kwargs.get("quality", "original")
        fn = functools.partial(
            self._convert_sync,
            input_path, input_format, output_format, output_path,
            quality=quality,
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
    ) -> None:
        from pydub import AudioSegment  # type: ignore

        read_fmt  = _PYDUB_READ.get(input_format, input_format)
        write_fmt = _PYDUB_WRITE.get(output_format)
        if write_fmt is None:
            raise ValueError(f"Unknown audio output format: {output_format!r}")

        audio = AudioSegment.from_file(str(input_path), format=read_fmt)

        export_kwargs: dict = {}

        # ── Lossless outputs: no bitrate parameters needed ────────────────────
        if output_format == "wav":
            pass  # pydub writes uncompressed PCM by default

        elif output_format == "flac":
            # compression_level only affects speed/size, not audio quality
            export_kwargs["parameters"] = ["-compression_level", "8"]

        # ── Lossless quality request → use highest preset for lossy outputs ──
        elif quality == "lossless":
            preset = _PRESETS["high"]
            if output_format == "mp3":
                export_kwargs["bitrate"] = preset["mp3"]
            elif output_format in ("aac", "m4a"):
                export_kwargs["bitrate"] = preset[output_format]
            elif output_format == "ogg":
                export_kwargs["parameters"] = ["-q:a", str(preset["ogg_q"])]
            log.info("audio %s → %s quality=lossless (using high preset)", input_format, output_format)

        # ── Lossy outputs: quality-aware bitrate selection ────────────────────
        elif quality == "original":
            # Probe the source and match its bitrate as closely as possible
            source_kbps = _probe_bitrate_kbps(input_path)
            log.debug(
                "source=%s detected_bitrate=%s kbps → target=%s",
                input_format, source_kbps, output_format,
            )

            if output_format == "mp3":
                br = _mp3_bitrate_for_source(source_kbps, input_format)
                export_kwargs["bitrate"] = br
                log.info("audio MP3: source=%s kbps → %s", source_kbps, br)

            elif output_format in ("aac", "m4a"):
                br = _aac_bitrate_for_source(source_kbps, input_format)
                export_kwargs["bitrate"] = br
                log.info("audio %s: source=%s kbps → %s", output_format.upper(), source_kbps, br)

            elif output_format == "ogg":
                q = _ogg_quality_for_source(source_kbps, input_format)
                export_kwargs["parameters"] = ["-q:a", str(q)]
                log.info("audio OGG: source=%s kbps → q:a %d", source_kbps, q)

        else:
            # Named quality preset ("high" / "medium" / "low")
            preset = _PRESETS.get(quality)
            if preset is None:
                raise ValueError(
                    f"Unknown quality level {quality!r}. "
                    f"Valid values: 'original', 'high', 'medium', 'low'."
                )

            if output_format == "mp3":
                export_kwargs["bitrate"] = preset["mp3"]
            elif output_format == "aac":
                export_kwargs["bitrate"] = preset["aac"]
            elif output_format == "m4a":
                export_kwargs["bitrate"] = preset["m4a"]
            elif output_format == "ogg":
                export_kwargs["parameters"] = ["-q:a", str(preset["ogg_q"])]

            log.info(
                "audio %s → %s quality=%s %s",
                input_format, output_format, quality, export_kwargs,
            )

        audio.export(str(output_path), format=write_fmt, **export_kwargs)
        log.info(
            "audio: %s → %s OK (%.1fs, quality=%s)",
            input_format, output_format, len(audio) / 1000, quality,
        )
