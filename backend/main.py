"""File Converter — FastAPI backend.

Endpoints:
    GET  /api/health                     → health check
    POST /api/upload                     → upload a single file, get format info
    POST /api/bulk-upload                → upload multiple files at once
    POST /api/convert                    → convert a single uploaded file
    POST /api/bulk-convert               → convert multiple files, download as ZIP
    GET  /api/download/{download_id}     → stream converted file (or ZIP)
"""

import asyncio
import json as _json
import logging
import shutil
import tempfile
import time
import uuid
import zipfile as _zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from converters import convert_file, detect_format, get_available_formats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fc.main")

# ── In-memory state ───────────────────────────────────────────────────────────
# Keyed by UUID strings; each entry expires after FILE_TTL seconds.

UPLOADS: dict[str, dict] = {}    # file_id  → {path, filename, format, category, expires_at}
DOWNLOADS: dict[str, dict] = {}  # download_id → {path, filename, expires_at}

TEMP_DIR = Path(tempfile.mkdtemp(prefix="fc_"))
FILE_TTL = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes

# Valid quality values accepted by all lossy converters
_VALID_QUALITY = {"original", "high", "medium", "low", "lossless"}

# ── Startup / shutdown ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Start background cleanup loop; tear down temp dir on exit."""
    task = asyncio.create_task(_cleanup_loop())
    log.info("File converter started. Temp dir: %s", TEMP_DIR)
    try:
        yield
    finally:
        task.cancel()
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        log.info("Temp dir removed. Shutdown complete.")


async def _cleanup_loop() -> None:
    """Periodically purge expired upload/download entries."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        _purge_expired()


def _purge_expired() -> None:
    now = time.time()
    removed = 0
    for store in (UPLOADS, DOWNLOADS):
        expired_keys = [k for k, v in store.items() if v.get("expires_at", 0) < now]
        for k in expired_keys:
            p = store[k].get("path")
            if p:
                Path(p).unlink(missing_ok=True)
            del store[k]
            removed += 1
    if removed:
        log.info("Cleanup: purged %d expired file(s)", removed)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="File Converter",
    version="1.0.0",
    description="Convert between document, image, audio, video, data, and archive formats.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Internal helpers ──────────────────────────────────────────────────────────


async def _store_upload(file: UploadFile) -> dict:
    """Read, detect format, persist one UploadFile. Returns the upload metadata dict."""
    filename = file.filename or "upload"
    content  = await file.read()

    try:
        fmt, category = detect_format(filename, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    file_id = str(uuid.uuid4())
    dest    = TEMP_DIR / f"{file_id}_{filename}"

    try:
        dest.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store upload: {exc}") from exc

    meta = {
        "path":       str(dest),
        "filename":   filename,
        "format":     fmt,
        "category":   category,
        "expires_at": time.time() + FILE_TTL,
    }
    UPLOADS[file_id] = meta
    log.info("Uploaded '%s' (%d B) fmt=%s cat=%s", filename, len(content), fmt, category)

    return {
        "file_id":          file_id,
        "filename":         filename,
        "size":             len(content),
        "detected_format":  fmt,
        "category":         category,
        "available_formats": get_available_formats(fmt, category),
    }


async def _do_one_conversion(
    file_id: str,
    target_format: str,
    quality: str,
) -> tuple[Path, str]:
    """Convert one uploaded file. Returns (output_path, output_filename).

    Raises ValueError for bad input, propagates converter exceptions on failure.
    """
    meta = UPLOADS.get(file_id)
    if meta is None:
        raise ValueError(f"Upload '{file_id}' not found or expired.")

    input_path = Path(meta["path"])
    if not input_path.exists():
        raise ValueError(f"Upload '{file_id}' file is no longer on disk.")

    target_format = target_format.lower().strip(". ")
    available = get_available_formats(meta["format"], meta["category"])
    if target_format not in available:
        raise ValueError(
            f"Cannot convert '{meta['format']}' to '{target_format}'. "
            f"Available: {available}"
        )

    stem    = Path(meta["filename"]).stem
    ext     = "tar.gz" if target_format == "tar.gz" else target_format
    out_fn  = f"{stem}.{ext}"
    conv_id = str(uuid.uuid4())
    out_path = TEMP_DIR / f"{conv_id}_{out_fn}"

    await convert_file(
        input_path=input_path,
        input_format=meta["format"],
        output_format=target_format,
        category=meta["category"],
        output_path=out_path,
        quality=quality,
    )

    log.info("Converted '%s' %s → %s", meta["filename"], meta["format"], target_format)
    return out_path, out_fn


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    """Return service health and version."""
    return {"status": "ok", "version": "1.0.0"}


# ── Single-file upload / convert / download ───────────────────────────────────

@app.post("/api/upload", tags=["single"])
async def upload(file: UploadFile = File(...)) -> dict:
    """Upload a single file and detect its format.

    Returns file_id, detected format, and the list of available output formats.
    """
    return await _store_upload(file)


@app.post("/api/convert", tags=["single"])
async def convert(
    file_id:       str = Form(...),
    target_format: str = Form(...),
    quality:       str = Form("original"),
) -> dict:
    """Convert a previously uploaded file to *target_format*.

    Args:
        file_id:       UUID returned by /api/upload.
        target_format: Desired output format (e.g. 'pdf', 'mp3').
        quality:       'original' (default) | 'high' | 'medium' | 'low' | 'lossless'.
                       Only affects lossy formats (audio/video); ignored otherwise.

    Returns download_id to pass to /api/download/{download_id}.
    """
    if quality not in _VALID_QUALITY:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quality '{quality}'. Valid values: {sorted(_VALID_QUALITY)}",
        )

    try:
        out_path, out_fn = await _do_one_conversion(file_id, target_format, quality)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Conversion failed: file_id=%s target=%s", file_id, target_format)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc

    download_id = str(uuid.uuid4())
    DOWNLOADS[download_id] = {
        "path":       str(out_path),
        "filename":   out_fn,
        "expires_at": time.time() + FILE_TTL,
    }

    return {"download_id": download_id, "output_filename": out_fn, "status": "ready"}


# ── Bulk upload / convert ─────────────────────────────────────────────────────

@app.post("/api/bulk-upload", tags=["bulk"])
async def bulk_upload(files: List[UploadFile] = File(...)) -> dict:
    """Upload multiple files at once.

    Returns a list of file metadata objects (one per file), each with:
    file_id, filename, size, detected_format, category, available_formats.
    Files that fail format detection are returned with an 'error' key instead.
    """
    results = []
    for f in files:
        try:
            results.append(await _store_upload(f))
        except HTTPException as exc:
            results.append({
                "filename": f.filename or "unknown",
                "error":    exc.detail,
            })

    return {"files": results, "count": len(results)}


@app.post("/api/bulk-convert", tags=["bulk"])
async def bulk_convert(
    conversions: str = Form(...),
    quality:     str = Form("original"),
) -> dict:
    """Convert multiple uploaded files and bundle results into a ZIP.

    Args:
        conversions: JSON array of objects: [{file_id, target_format}, ...]
        quality:     Applied to all conversions. Same values as /api/convert.

    Returns download_id pointing to the resulting ZIP archive.
    The response also contains per-file status and any errors.
    """
    if quality not in _VALID_QUALITY:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quality '{quality}'. Valid values: {sorted(_VALID_QUALITY)}",
        )

    try:
        items: list[dict] = _json.loads(conversions)
    except _json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in 'conversions': {exc}") from exc

    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="'conversions' must be a non-empty JSON array.")

    # Run all conversions concurrently — each uses run_in_executor internally
    tasks = [
        _do_one_conversion(item.get("file_id", ""), item.get("target_format", ""), quality)
        for item in items
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successes from failures
    successes: list[tuple[Path, str]] = []
    errors: list[dict] = []

    for i, result in enumerate(raw_results):
        item = items[i]
        if isinstance(result, Exception):
            errors.append({
                "file_id":       item.get("file_id"),
                "target_format": item.get("target_format"),
                "error":         str(result),
            })
            log.warning("Bulk conversion failed for file_id=%s: %s", item.get("file_id"), result)
        else:
            successes.append(result)

    if not successes:
        raise HTTPException(
            status_code=422,
            detail=f"All {len(errors)} conversion(s) failed. Errors: {errors}",
        )

    # Bundle all successful outputs into a single ZIP
    zip_download_id = str(uuid.uuid4())
    zip_path = TEMP_DIR / f"{zip_download_id}_converted.zip"

    with _zipfile.ZipFile(zip_path, "w", _zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for out_path, out_fn in successes:
            zf.write(out_path, arcname=out_fn)
            out_path.unlink(missing_ok=True)  # remove individual file after packing

    DOWNLOADS[zip_download_id] = {
        "path":       str(zip_path),
        "filename":   "converted.zip",
        "expires_at": time.time() + FILE_TTL,
    }

    log.info(
        "Bulk convert: %d succeeded, %d failed → converted.zip",
        len(successes), len(errors),
    )

    return {
        "download_id":     zip_download_id,
        "output_filename": "converted.zip",
        "count":           len(successes),
        "errors":          errors,
    }


# ── Download (shared by single and bulk) ─────────────────────────────────────

@app.get("/api/download/{download_id}", tags=["single", "bulk"])
async def download(download_id: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Stream the converted file (or ZIP) to the client, then clean it up."""
    dl = DOWNLOADS.get(download_id)
    if dl is None:
        raise HTTPException(status_code=404, detail="Download not found or already consumed.")

    out_path = Path(dl["path"])
    if not out_path.exists():
        DOWNLOADS.pop(download_id, None)
        raise HTTPException(status_code=410, detail="File is no longer available.")

    def _cleanup() -> None:
        out_path.unlink(missing_ok=True)
        DOWNLOADS.pop(download_id, None)
        log.info("Download consumed: %s", dl["filename"])

    background_tasks.add_task(_cleanup)

    return FileResponse(
        path=str(out_path),
        filename=dl["filename"],
        media_type="application/octet-stream",
    )


# ── Serve frontend static files ──────────────────────────────────────────────
# Must be mounted AFTER all /api routes so it doesn't shadow them.

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"  # local dev
if not _FRONTEND_DIR.is_dir():
    _FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"   # Docker
if _FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
