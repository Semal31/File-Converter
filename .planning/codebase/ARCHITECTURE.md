# Architecture

**Analysis Date:** 2026-02-24

## Pattern Overview

**Overall:** Modular converter dispatcher with category-based routing.

**Key Characteristics:**
- Single FastAPI application serving HTTP endpoints
- Pluggable converter modules organized by file category (document, image, audio, video, data, archive)
- In-memory state management with automatic TTL-based cleanup
- Async-to-sync bridge pattern for long-running conversions
- Format detection via extension mapping at application startup

## Layers

**API / HTTP Layer:**
- Purpose: Handle client requests, manage session state, coordinate uploads/conversions/downloads
- Location: `backend/main.py`
- Contains: FastAPI routes, endpoint handlers, form/file parsing
- Depends on: Converter package (format detection and conversion dispatch)
- Used by: Frontend client (HTML/JS)

**Converter Package:**
- Purpose: Format detection, converter registration, conversion dispatch
- Location: `backend/converters/__init__.py`
- Contains: Format registry, extension→format mapping, public API (detect_format, convert_file, get_available_formats)
- Depends on: Individual converter modules (documents, images, audio, video, data, archives)
- Used by: API layer via `convert_file()` and `detect_format()`

**Category-Specific Converters:**
- Purpose: Implement format-to-format conversion for a specific media category
- Locations: `backend/converters/{documents,images,audio,video,data,archives}.py`
- Contains: Format metadata (extensions, codec maps), conversion logic, quality presets
- Depends on: Third-party libraries (pypandoc, Pillow, pydub, ffmpeg, pandas, etc.)
- Used by: Converter package via `convert()` method

**Frontend:**
- Purpose: User interface for file selection, format choice, quality setting, download
- Location: `frontend/index.html`
- Contains: HTML/CSS/JS single-page application with dark theme
- Depends on: Backend API endpoints
- Used by: End user

## Data Flow

**Upload + Detection Flow:**

1. Client submits file via POST `/api/upload` (single) or `/api/bulk-upload` (multiple)
2. API receives `UploadFile`, reads bytes to memory
3. Calls `detect_format(filename, content_type)` from converter package
4. Format detection uses extension map `_EXT_MAP` (built at startup) to find canonical format and category
5. Raises `ValueError` if extension not recognized (returned as HTTP 400)
6. File stored in temp directory under UUID filename: `{TEMP_DIR}/{file_id}_{original_filename}`
7. Returns metadata: `{file_id, filename, size, detected_format, category, available_formats}`

**Conversion Flow:**

1. Client submits conversion request via POST `/api/convert` with `{file_id, target_format, quality}`
2. API validates quality against `_VALID_QUALITY = {original, high, medium, low, lossless}`
3. Calls `_do_one_conversion(file_id, target_format, quality)`
4. Retrieves metadata from `UPLOADS[file_id]` (validates file still exists)
5. Validates target format is in `get_available_formats(format, category)`
6. Calls `await convert_file(input_path, input_format, output_format, category, output_path, quality=quality)`
7. Converter package dispatches to appropriate converter module's `convert()` method
8. Converter runs sync work in executor thread pool (via `loop.run_in_executor()`)
9. Returns output file path and filename
10. Stores result in `DOWNLOADS[download_id]` and returns download token to client

**Bulk Conversion Flow:**

1. Client submits POST `/api/bulk-convert` with JSON array: `[{file_id, target_format}, ...]`
2. API parses JSON and validates all quality/format values
3. Creates async tasks for each item, runs concurrently via `asyncio.gather(*tasks, return_exceptions=True)`
4. Collects successes and failures from results
5. If any successes: bundles all output files into ZIP with `zipfile.ZipFile`, stores in `DOWNLOADS`
6. If all fail: raises HTTP 422 with error details
7. Returns ZIP download token and per-file status

**Download + Cleanup Flow:**

1. Client requests GET `/api/download/{download_id}`
2. API retrieves from `DOWNLOADS[download_id]`
3. Returns `FileResponse` (streams file as octet-stream)
4. Registers background task to delete file and remove from `DOWNLOADS` dict after response sent

**Background Cleanup Loop:**

1. Started at app startup via `lifespan` context manager
2. Runs every `CLEANUP_INTERVAL` (300s)
3. Checks `expires_at` timestamp on all entries in `UPLOADS` and `DOWNLOADS`
4. Deletes expired files from disk and dict entries
5. Continues until app shutdown (cancels on exception)

**State Management:**

- In-memory: `UPLOADS` dict and `DOWNLOADS` dict keyed by UUID
- File storage: Temporary directory created at startup (`TEMP_DIR = Path(tempfile.mkdtemp(prefix="fc_"))`)
- TTL: `FILE_TTL = 3600` seconds (1 hour) per file
- No persistence between restarts
- No distributed state (single-instance only)

## Key Abstractions

**BaseConverter:**
- Purpose: Define interface all category-specific converters must implement
- Examples: `backend/converters/{documents,images,audio,video,data,archives}.py`
- Pattern: Abstract base class with four required methods:
  - `supported_formats` (property) → list of canonical format names
  - `format_extensions(fmt)` → list of file extensions for that format
  - `get_output_formats(input_format)` → list of valid target formats
  - `convert(input_path, input_format, output_format, output_path, **kwargs)` → async conversion

**Converter Registry:**
- Pattern: Singleton dict instantiated at module load
- Location: `backend/converters/__init__.py` line 20-27
- Maps category name → converter instance: `{"document": DocumentConverter(), "image": ImageConverter(), ...}`
- Built once at import time, immutable during runtime

**Extension Map:**
- Pattern: Pre-computed lookup table built at startup
- Location: `backend/converters/__init__.py` line 31-36
- Maps file extension → (canonical_format, category) tuple
- Enables O(1) format detection on upload

**Async-to-Sync Bridge:**
- Pattern: All converters implement async `convert()` but do sync work
- Method: `loop.run_in_executor(None, self._convert_sync, ...)`
- Purpose: Prevent blocking event loop during CPU-intensive conversions
- Example: `backend/converters/documents.py` line 64-66

**Quality Parameter Passthrough:**
- Pattern: Converters accept `**kwargs` in `convert()`, extract what they use, ignore rest
- Used by: Audio (bitrate control), Video (CRF/quality presets)
- Ignored by: Documents, Images, Data, Archives
- Values: `{original, high, medium, low, lossless}` (validated at API layer)

## Entry Points

**Server Startup:**
- Location: `backend/main.py` line 87-92 (`app = FastAPI(...)`)
- Triggers: `uvicorn main:app --host 0.0.0.0 --port 8070` (via run.sh)
- Responsibilities:
  - Initialize FastAPI app with CORS middleware (allow all origins)
  - Register lifespan context manager (starts cleanup loop)
  - Mount static frontend files at root after API routes

**Request Entry Points:**

- `POST /api/health` → Returns `{status, version}` for readiness checks

- `POST /api/upload` → Single file upload (line 197-203)
  - Triggers: `_store_upload()` → format detection → in-memory storage
  - Returns: File metadata + available output formats

- `POST /api/convert` → Single conversion (line 206-243)
  - Triggers: `_do_one_conversion()` → converter dispatch → file storage
  - Returns: Download token

- `POST /api/bulk-upload` → Batch upload (line 248-266)
  - Triggers: Multiple `_store_upload()` calls
  - Returns: Array of file metadata or errors

- `POST /api/bulk-convert` → Batch conversion (line 269-351)
  - Triggers: Multiple `_do_one_conversion()` tasks (concurrent)
  - Returns: ZIP download token + per-file status

- `GET /api/download/{download_id}` → File delivery (line 356-379)
  - Triggers: `FileResponse` stream + background cleanup
  - Returns: File bytes

**Frontend Entry:**
- Location: `frontend/index.html`
- Serves as SPA, mounted at `/` after all `/api/*` routes (FastAPI `mount()`)
- Single HTML file contains all CSS and JS inline

## Error Handling

**Strategy:** Validation at API layer, conversion errors propagated to client with context.

**Patterns:**

- **Format Detection Errors:** Caught as `ValueError`, returned as HTTP 400 with detail message
  - Example: `"Unsupported format '.xyz'. Supported extensions: ..."`

- **File Not Found:** Checked before conversion, returned as HTTP 400
  - Handles case where upload expired between upload and conversion request

- **Invalid Conversion Target:** Validated against `get_available_formats()`, HTTP 400 if not allowed
  - Example: PDF inputs cannot be converted (pandoc limitation)

- **Conversion Failures:** Caught in try/except, logged with context, returned as HTTP 500
  - Bulk conversions: collected as per-file errors, HTTP 422 if all fail
  - Single conversions: HTTP 500 with exception message

- **Download Not Found:** HTTP 404 if download token expired or already consumed
  - HTTP 410 if file deleted from disk but token still valid

- **Quality Validation:** Pre-checked against `_VALID_QUALITY` set, HTTP 400 if invalid
  - Applied to all conversions uniformly before dispatching to converter

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Locations: Loggers created per module (`fc.main`, `fc.documents`, `fc.audio`, etc.)
- Pattern: Log at INFO for significant operations (upload, conversion, cleanup), DEBUG/WARNING for edge cases
- Example: `log.info("Converted '%s' %s → %s", filename, format_in, format_out)`

**Validation:**
- File extension → format: Built into `_EXT_MAP`, checked in `detect_format()`
- Format compatibility: Checked via `get_available_formats()` before conversion
- Quality parameter: Validated against `_VALID_QUALITY` set before any conversion
- Target format case-normalization: `target_format.lower().strip(". ")` to handle user typos

**CORS:**
- Allow all origins via `CORSMiddleware` on app (line 94-99)
- In Docker, nginx proxies `/api/*` requests (no CORS needed)
- In local dev, frontend runs on same origin as backend (`localhost:8070`)

**Temporary File Management:**
- Creation: `write_bytes(content)` to temp directory
- Naming: UUID prefixed to avoid collisions: `{file_id}_{original_filename}`
- Cleanup: Via TTL expiry (background loop) or after download (background task)
- Directory: Removed entirely on app shutdown via `shutil.rmtree(TEMP_DIR, ignore_errors=True)`

**Concurrency:**
- Request handling: FastAPI/uvicorn async per-request
- CPU-bound work: Offloaded to executor thread pool via `run_in_executor()`
- Bulk conversions: Multiple conversions concurrent via `asyncio.gather()`
- State access: No locking (single-instance, Python GIL, mutation-free operations)

---

*Architecture analysis: 2026-02-24*
