# Coding Conventions

**Analysis Date:** 2026-02-24

## Naming Patterns

**Files:**
- Module files: `lowercase_with_underscores.py` (e.g., `audio.py`, `archives.py`)
- Converter implementations: `{type}s.py` pattern (e.g., `images.py`, `documents.py`, `videos.py`)
- Base/abstract files: `base.py`
- Package entry: `__init__.py`
- Main application: `main.py`

**Functions:**
- Private functions: `_snake_case` prefix (e.g., `_store_upload`, `_do_one_conversion`, `_convert_sync`)
- Public/async functions: `snake_case` without prefix (e.g., `convert_file`, `detect_format`, `health`)
- Helper functions within classes: `_method_name` prefix (e.g., `_svg_to_png_bytes`, `_probe_bitrate_kbps`)
- Constants/configuration functions: `_snake_case` (e.g., `_cleanup_loop`, `_purge_expired`)

**Variables:**
- Module-level constants: `_UPPERCASE_WITH_UNDERSCORES` (e.g., `_EXTENSIONS`, `_PRESETS`, `_VALID_QUALITY`)
- Local variables: `snake_case` (e.g., `file_id`, `output_format`, `export_kwargs`)
- Dictionary keys: `lowercase` (e.g., `path`, `filename`, `format`, `category`)
- Type abbreviations: `_CONVERTERS`, `_EXT_MAP`, `_PYDUB_WRITE`

**Types:**
- Classes: `PascalCase` (e.g., `BaseConverter`, `ImageConverter`, `AudioConverter`, `VideoConverter`)
- Type hints use built-in generics: `dict[str, str]`, `list[str]`, `tuple[str, str]`, `Path`, `None`
- Return type annotations: Always included (e.g., `-> dict`, `-> None`, `-> tuple[Path, str]`)

## Code Style

**Formatting:**
- Line length: No strict limit enforced, but most lines stay under 100 characters
- Indentation: 4 spaces (Python standard)
- String quotes: Double quotes preferred (`"string"` not `'string'`)
- Spacing: Standard PEP 8 spacing around operators and after commas

**Linting:**
- No `.flake8`, `.pylintrc`, or `ruff.toml` configured
- No formatting tool configured (no `.prettierrc` equivalent)
- Code follows Python conventions informally without linter enforcement

## Import Organization

**Order:**
1. Standard library imports (`asyncio`, `json`, `logging`, `pathlib`, `typing`)
2. Third-party imports (`fastapi`, `pydub`, `pillow`, `pandas`)
3. Relative imports (`from .base import BaseConverter`, `from .converters import ...`)

**Path Aliases:**
- No path aliases configured; relative imports use `from .module import Class`
- Common pattern: `from .base import BaseConverter` in all converter modules

**Import Style:**
```python
# Imports at module top
import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException

from converters import convert_file, detect_format, get_available_formats
```

## Error Handling

**Patterns:**

**ValueError for domain logic errors:**
```python
# In converters/__init__.py
raise ValueError(f"Unsupported format '.{ext}'. Supported extensions: ...")

# In main.py _do_one_conversion
raise ValueError(f"Upload '{file_id}' not found or expired.")
```

**HTTPException for API errors:**
```python
# Map ValueError to 400 Bad Request
try:
    fmt, category = detect_format(filename, file.content_type)
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc

# Generic exceptions → 500 Internal Server Error
except Exception as exc:
    log.exception("Conversion failed: file_id=%s target=%s", file_id, target_format)
    raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc
```

**Exceptions with context:**
- Always use `from exc` to preserve traceback
- Capture exceptions with descriptive error messages
- Log full exceptions with `log.exception()` for unexpected errors

**Silent failures with defaults:**
```python
# Return safe defaults on failure (see video.py)
def _probe_video(path: Path) -> dict:
    try:
        import ffmpeg
        # ... probe logic
    except Exception as exc:
        log.debug("ffprobe failed for %s: %s", path.name, exc)
    return {"width": 0, "height": 0, "fps": 24.0}  # safe default
```

## Logging

**Framework:** Python standard library `logging`

**Setup pattern (main.py):**
```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fc.main")
```

**Logger naming:** `"fc.{module}"` prefix (e.g., `"fc.main"`, `"fc.audio"`, `"fc.images"`)

**Logging Patterns:**

**Info level (successful operations):**
```python
log.info("File converter started. Temp dir: %s", TEMP_DIR)
log.info("Uploaded '%s' (%d B) fmt=%s cat=%s", filename, len(content), fmt, category)
log.info("Converted '%s' %s → %s", meta["filename"], meta["format"], target_format)
log.info("Cleanup: purged %d expired file(s)", removed)
```

**Debug level (diagnostic info):**
```python
log.debug("ffprobe failed for %s: %s", path.name, exc)
log.debug("source=%s detected_bitrate=%s kbps → target=%s", input_format, source_kbps, output_format)
```

**Warning level (recoverable issues):**
```python
log.warning("Bulk conversion failed for file_id=%s: %s", item.get("file_id"), result)
```

**Exception level (unhandled errors):**
```python
log.exception("Conversion failed: file_id=%s target=%s", file_id, target_format)
```

## Comments

**When to Comment:**
- Module docstrings: Always (3-line format with endpoint list for main.py, feature list for converters)
- Function docstrings: For public functions and complex private methods
- Inline comments: Only for non-obvious logic or important caveats
- No comments for obvious code

**Docstring Style:**
```python
"""Convert any document format to PDF.

Strategy:
1. If input is already HTML, feed directly to weasyprint.
2. Otherwise convert to HTML via pandoc first, then weasyprint.
"""

async def _store_upload(file: UploadFile) -> dict:
    """Read, detect format, persist one UploadFile. Returns the upload metadata dict."""
```

**Comments for Design Rationale:**
```python
# Re-encoding lossy→lossy at a *lower* bitrate always loses quality; at the
# same bitrate there is still generational loss, so we stay at or above.

# GIF has size constraints
if save_fmt == "ICO":
    img = img.convert("RGBA")
    img.save(str(output_path), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
```

## Function Design

**Size:** Functions are concise but comprehensive, typically 20-50 lines for async methods

**Parameters:**
- Path objects use `Path` type (not strings)
- Format strings use lowercase identifiers: `"pdf"`, `"mp3"`, `"jpeg"`
- Dictionary parameters passed as kwargs: `**kwargs` with documented extraction pattern
- Boolean/quality parameters passed explicitly, not through kwargs

**Return Values:**
- Explicit return types always specified
- None for side-effect-only functions
- Tuples for multiple related returns: `tuple[Path, str]`
- Dictionaries for structured data: `dict[str, Any]`

**Async Pattern:**
```python
async def convert(
    self,
    input_path: Path,
    input_format: str,
    output_format: str,
    output_path: Path,
    **kwargs,
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, self._convert_sync, input_path, ...)
```

## Module Design

**Exports:**
- Public API functions exported at package level (`from converters import convert_file`)
- Private implementation details prefixed with `_` (e.g., `_store_upload`)
- Converter classes imported but not re-exported in `__init__.py`

**Converters Pattern:**
```python
# All converters implement BaseConverter interface
class ImageConverter(BaseConverter):
    @property
    def supported_formats(self) -> list[str]:
        ...

    def format_extensions(self, fmt: str) -> list[str]:
        ...

    def get_output_formats(self, input_format: str) -> list[str]:
        ...

    async def convert(...) -> None:
        ...
```

**Format Metadata Organization:**
Each converter module uses consistent structure:
```python
_EXTENSIONS: dict[str, list[str]] = { ... }  # Format → file extensions
_PYDUB_WRITE: dict[str, str] = { ... }       # Format → library format strings
_PRESETS: dict[str, dict] = { ... }          # Quality → bitrate settings
_LOSSLESS: set[str] = { ... }                # Lossless format set
```

## Project Structure Conventions

**Backend organization (`/backend`):**
- `main.py`: FastAPI app, endpoints, file storage management
- `converters/`: Format conversion implementations
  - `__init__.py`: Public API, converter registry, format detection
  - `base.py`: Abstract BaseConverter interface
  - `{type}s.py`: Category converters (images.py, audio.py, documents.py, video.py, data.py, archives.py)

**Temp file naming:**
```python
# For uploads: {uuid}_{original_filename}
dest = TEMP_DIR / f"{file_id}_{filename}"

# For conversions: {uuid}_{stem}.{ext}
out_path = TEMP_DIR / f"{conv_id}_{out_fn}"
```

**State storage:**
```python
UPLOADS: dict[str, dict] = {}     # file_id → {path, filename, format, category, expires_at}
DOWNLOADS: dict[str, dict] = {}   # download_id → {path, filename, expires_at}
```

---

*Convention analysis: 2026-02-24*
