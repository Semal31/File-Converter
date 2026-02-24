"""File Converter -- FastAPI backend.

Endpoints:
    GET  /api/health                     -> health check
    POST /api/upload                     -> upload a single file, get format info
    POST /api/bulk-upload                -> upload multiple files at once
    POST /api/convert                    -> start async conversion, get job_id
    POST /api/bulk-convert               -> start async conversions, get per-file job_ids
    GET  /api/progress/{job_id}          -> SSE stream of job progress events
    GET  /api/download/{download_id}     -> stream converted file
"""

import asyncio
import json as _json
import logging
import os
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette import EventSourceResponse

from converters import convert_file, detect_format, get_available_formats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fc.main")

# ── In-memory state ───────────────────────────────────────────────────────────
# Keyed by UUID strings; each entry expires after FILE_TTL seconds.

UPLOADS: dict[str, dict] = {}    # file_id  → {path, filename, format, category, expires_at}
DOWNLOADS: dict[str, dict] = {}  # download_id → {path, filename, expires_at}
JOBS: dict[str, dict] = {}  # job_id → {state, percent, download_id, message, detail, expires_at}

_RUNNING_TASKS: set[asyncio.Task] = set()


def _spawn_job_task(coro) -> asyncio.Task:
    """Fire-and-forget with reference tracking to prevent GC."""
    task = asyncio.create_task(coro)
    _RUNNING_TASKS.add(task)
    task.add_done_callback(_RUNNING_TASKS.discard)
    return task

TEMP_DIR = Path(tempfile.mkdtemp(prefix="fc_"))
FILE_TTL = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes

# Valid quality values accepted by all lossy converters
_VALID_QUALITY = {"original", "high", "medium", "low", "lossless"}

# Binaries that must be on PATH for conversions to work.
# Maps binary name → install hint for the error message.
_REQUIRED_BINARIES: dict[str, str] = {
    "pandoc": "apt-get install pandoc",
    "ffmpeg": "apt-get install ffmpeg",
}

# ── Startup / shutdown ────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Validate system dependencies, then start background cleanup loop."""
    # ── Startup validation ────────────────────────────────────────────────
    missing: list[str] = []

    # 1. Check required external binaries
    for binary, install_hint in _REQUIRED_BINARIES.items():
        if shutil.which(binary) is None:
            missing.append(
                f"  - '{binary}' not found on PATH. Fix: {install_hint}"
            )

    # 2. Check WeasyPrint can import (validates cairo/pango system libs)
    try:
        import weasyprint  # noqa: F401
    except Exception as exc:
        missing.append(
            f"  - weasyprint failed to import: {exc}\n"
            "    Fix: ensure libpangoft2-1.0-0 and libharfbuzz-subset0 are installed."
        )

    if missing:
        log.critical(
            "STARTUP ERROR — required system dependencies are missing:\n%s\n"
            "Container cannot serve requests. Exiting.",
            "\n".join(missing),
        )
        os._exit(1)  # Bypass exception handlers; exit unconditionally

    log.info("Startup checks passed. All required binaries present.")

    # ── Background cleanup loop ───────────────────────────────────────────
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
    for store in (UPLOADS, DOWNLOADS, JOBS):
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


@app.exception_handler(HTTPException)
async def structured_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Normalize all HTTP errors to {message, detail} shape."""
    if isinstance(exc.detail, dict) and "message" in exc.detail:
        body = exc.detail
    else:
        body = {"message": str(exc.detail), "detail": None}
    return JSONResponse(status_code=exc.status_code, content=body)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _classify_exc(exc: Exception) -> tuple[str, str | None]:
    """Map a converter exception to (user_message, raw_detail).

    user_message: plain English, safe to show in the UI.
    raw_detail:   technical string for "Show details" toggle, or None.
    """
    import ffmpeg as _ffmpeg
    from pydub.exceptions import CouldntDecodeError, CouldntEncodeError

    raw = str(exc)

    # ffmpeg-python: .stderr is bytes | None
    if isinstance(exc, _ffmpeg.Error):
        stderr_bytes = exc.stderr or b""
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
        lines = [
            l.strip() for l in stderr.splitlines()
            if l.strip() and not l.lstrip().startswith("ffmpeg version")
        ]
        hint = lines[-1] if lines else "ffmpeg processing failed"
        return f"Conversion failed: {hint}", stderr

    # pydub wraps ffmpeg decode/encode — str(exc) leaks subprocess output
    if isinstance(exc, (CouldntDecodeError, CouldntEncodeError)):
        action = "decode" if isinstance(exc, CouldntDecodeError) else "encode"
        return (
            f"Audio {action} failed. The file may be corrupt or use an unsupported codec.",
            raw,
        )

    # pypandoc raises RuntimeError with pandoc stderr embedded in str(exc)
    if isinstance(exc, RuntimeError) and "pandoc" in raw.lower():
        return (
            "Document conversion failed. The file may be malformed or contain unsupported features.",
            raw,
        )

    # Pillow image read failure (Pillow >= 7.2, project requires >= 10.2)
    try:
        from PIL import UnidentifiedImageError
        if isinstance(exc, UnidentifiedImageError):
            return "Image format not recognized. The file may be corrupt.", raw
    except ImportError:
        pass

    # pandas: malformed tabular data
    try:
        import pandas as pd
        if isinstance(exc, pd.errors.ParserError):
            return "Data file could not be parsed. Check that the file is well-formed.", raw
        if isinstance(exc, pd.errors.EmptyDataError):
            return "Data file is empty.", raw
    except ImportError:
        pass

    # ValueError from converters: messages already written as user-facing strings
    if isinstance(exc, ValueError):
        return raw, None

    # OSError: disk full, file permission error
    if isinstance(exc, OSError):
        return "File I/O error during conversion.", raw

    # Catch-all
    return "Conversion failed due to an unexpected error.", raw


async def _store_upload(file: UploadFile) -> dict:
    """Read, detect format, persist one UploadFile. Returns the upload metadata dict."""
    filename = file.filename or "upload"
    content  = await file.read()

    try:
        fmt, category = detect_format(filename, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "detail": None}) from exc

    file_id = str(uuid.uuid4())
    dest    = TEMP_DIR / f"{file_id}_{filename}"

    try:
        dest.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail={"message": "Failed to store upload.", "detail": str(exc)}) from exc

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
    progress_callback=None,
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
        targets = ", ".join(available)
        raise ValueError(
            f"Cannot convert {meta['format'].upper()} to {target_format.upper()}. "
            f"Available targets: {targets}."
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
        progress_callback=progress_callback,
    )

    log.info("Converted '%s' %s → %s", meta["filename"], meta["format"], target_format)
    return out_path, out_fn


async def _run_job(job_id: str, file_id: str, target_format: str, quality: str) -> None:
    """Background job: run conversion, update JOBS dict on completion or error."""
    def _progress(pct: float) -> None:
        job = JOBS.get(job_id)
        if job:
            job["percent"] = int(min(99, pct))  # hold at 99 until truly done

    try:
        out_path, out_fn = await _do_one_conversion(
            file_id, target_format, quality, progress_callback=_progress
        )
        download_id = str(uuid.uuid4())
        DOWNLOADS[download_id] = {
            "path": str(out_path),
            "filename": out_fn,
            "expires_at": time.time() + FILE_TTL,
        }
        JOBS[job_id].update({
            "state": "done",
            "percent": 100,
            "download_id": download_id,
            "expires_at": time.time() + FILE_TTL,
        })
        log.info("Job %s done -> download_id=%s", job_id, download_id)
    except Exception as exc:
        msg, raw = _classify_exc(exc)
        log.exception("Job %s failed", job_id)
        JOBS[job_id].update({
            "state": "error",
            "message": msg,
            "detail": raw,
            "expires_at": time.time() + FILE_TTL,
        })


def _terminal_payload(job: dict) -> dict:
    """Build the SSE payload for a done or error event."""
    if job["state"] == "done":
        return {"state": "done", "percent": 100, "download_id": job["download_id"]}
    return {"state": "error", "message": job["message"], "detail": job["detail"]}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/api/health", tags=["meta"])
async def health() -> dict:
    """Return service health and version."""
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/progress/{job_id}", tags=["progress"])
async def progress(job_id: str, request: Request):
    """Stream SSE events for a conversion job."""
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"message": f"Job '{job_id}' not found.", "detail": None})

    async def _stream():
        # Late-connect: if already terminal, send immediately and close
        job = JOBS.get(job_id)
        if job and job["state"] in ("done", "error"):
            yield {"data": _json.dumps(_terminal_payload(job))}
            return

        # Poll at 1-second intervals
        last_pct = -1
        while True:
            if await request.is_disconnected():
                return
            job = JOBS.get(job_id, {})
            state = job.get("state", "error")
            pct = job.get("percent", 0)

            if state in ("done", "error"):
                yield {"data": _json.dumps(_terminal_payload(job))}
                return

            if pct != last_pct:
                yield {"data": _json.dumps({"state": "running", "percent": pct})}
                last_pct = pct

            await asyncio.sleep(1)

    return EventSourceResponse(_stream(), ping=15)


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
            detail={"message": f"Invalid quality '{quality}'.", "detail": None},
        )

    try:
        out_path, out_fn = await _do_one_conversion(file_id, target_format, quality)
    except ValueError as exc:
        msg, raw = _classify_exc(exc)
        raise HTTPException(status_code=400, detail={"message": msg, "detail": raw}) from exc
    except Exception as exc:
        log.exception("Conversion failed: file_id=%s target=%s", file_id, target_format)
        msg, raw = _classify_exc(exc)
        raise HTTPException(status_code=500, detail={"message": msg, "detail": raw}) from exc

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
            err_detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail), "detail": None}
            results.append({
                "filename": f.filename or "unknown",
                "error":    err_detail.get("message", str(exc.detail)),
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
            detail={"message": f"Invalid quality '{quality}'.", "detail": None},
        )

    try:
        items: list[dict] = _json.loads(conversions)
    except _json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail={"message": f"Invalid JSON in 'conversions': {exc}", "detail": None}) from exc

    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail={"message": "'conversions' must be a non-empty JSON array.", "detail": None})

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
            msg, raw = _classify_exc(result)
            errors.append({
                "file_id":       item.get("file_id"),
                "target_format": item.get("target_format"),
                "message":       msg,
                "detail":        raw,
            })
            log.warning("Bulk conversion failed for file_id=%s: %s", item.get("file_id"), result)
        else:
            successes.append(result)

    if not successes:
        raise HTTPException(
            status_code=422,
            detail={"message": f"All {len(errors)} conversion(s) failed.", "detail": None},
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
        raise HTTPException(status_code=404, detail={"message": "Download not found or already consumed.", "detail": None})

    out_path = Path(dl["path"])
    if not out_path.exists():
        DOWNLOADS.pop(download_id, None)
        raise HTTPException(status_code=410, detail={"message": "File is no longer available.", "detail": None})

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
