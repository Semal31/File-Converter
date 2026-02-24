# Codebase Concerns

**Analysis Date:** 2026-02-24

## Tech Debt

**In-memory file tracking without persistence:**
- Issue: Uploads and downloads are stored in Python dictionaries (`UPLOADS`, `DOWNLOADS`) in `/home/semal/code-projects/file-converter/backend/main.py` (lines 37-38). All state is lost on server restart.
- Files: `backend/main.py`
- Impact: Users cannot resume conversions after app restart. In distributed deployments with multiple instances, file_id from one instance is invisible to others. No audit trail or analytics.
- Fix approach: Migrate to persistent storage (database like SQLite or PostgreSQL, or Redis for faster in-memory state). Implement proper session/state management that survives restarts.

**Monolithic file in frontend:**
- Issue: Entire frontend is a single 56KB HTML file with all CSS and JavaScript inline (`frontend/index.html`).
- Files: `frontend/index.html`
- Impact: Hard to maintain, test, or reuse components. No code reuse across features. CSS and JS minification/optimization difficult. Makes it hard to add features or fix bugs modularly.
- Fix approach: Split into separate files or modules. Consider using a frontend build tool (webpack, esbuild, or Vite) to create a proper SPA with component architecture.

**Temporary file cleanup relies on async background task:**
- Issue: File cleanup depends on a background loop in `/home/semal/code-projects/file-converter/backend/main.py` (lines 63-67) running every 5 minutes (`CLEANUP_INTERVAL = 300`). No guarantee the loop will run reliably under heavy load.
- Files: `backend/main.py`
- Impact: Disk space can fill up if cleanup loop falls behind. Temp directory grows uncontrolled in high-concurrency scenarios. TTL-based cleanup is race-prone (file can be deleted while still being served).
- Fix approach: Use deterministic cleanup on download completion (already partially done at line 373). Add metrics to track temp directory size. Consider using context managers or file handles to ensure cleanup even on error.

**Exception handling swallows specifics in bulk convert:**
- Issue: In `backend/main.py` line 302, `asyncio.gather(..., return_exceptions=True)` catches all exceptions but only logs warnings for failed conversions (line 316). The actual converter exception details are truncated.
- Files: `backend/main.py`
- Impact: Hard to debug why specific conversions fail in bulk operations. Users get generic "error" messages without useful detail.
- Fix approach: Capture and preserve full exception tracebacks. Include error type and stack context in the API response for bulk operations.

**No input validation on file paths before conversion:**
- Issue: File paths are constructed from user-supplied filenames at line 115 in `/home/semal/code-projects/file-converter/backend/main.py` (`dest = TEMP_DIR / f"{file_id}_{filename}"`). While UUIDs prevent collisions, malicious filenames with path traversal characters aren't explicitly validated.
- Files: `backend/main.py`
- Impact: Potential for unexpected behavior if filename contains special characters or is crafted to cause issues in downstream tools (ffmpeg, pandoc, etc.).
- Fix approach: Sanitize filenames explicitly. Strip or reject path separators, null bytes, and control characters before writing.

**No maximum file size limit:**
- Issue: The `upload` endpoint in `backend/main.py` (lines 198-203) accepts files of any size. Content is fully loaded into memory via `file.read()` at line 107.
- Files: `backend/main.py`
- Impact: Large files (GB+) can exhaust memory or disk. No protection against DoS attacks via large file uploads. Docker instance with limited resources can crash.
- Fix approach: Add configurable max upload size. Stream large files to disk instead of buffering in memory. Set limits in FastAPI config and nginx (if used).

**CORS is too permissive:**
- Issue: `CORSMiddleware` at line 94-99 in `/home/semal/code-projects/file-converter/backend/main.py` allows `allow_origins=["*"]` and `allow_headers=["*"]`.
- Files: `backend/main.py`
- Impact: Any website can make requests to your file converter API. No protection against cross-origin attacks. If credentials are added later, CORS will need rework.
- Fix approach: Restrict origins to known frontend domains (e.g., `allow_origins=["https://yourdomain.com"]`). Use explicit header lists instead of wildcard.

## Known Bugs

**Archive extraction does not validate zip file members consistently:**
- Symptoms: Path traversal check at line 77 in `/home/semal/code-projects/file-converter/backend/converters/archives.py` is checked for ZIP but not enforced for TAR files (lines 82-85).
- Files: `backend/converters/archives.py`
- Trigger: Extract a tar archive with `../` in member names (e.g., `../../etc/passwd`). The check at line 77 is ZIP-specific and silently skipped for TAR.
- Workaround: Use `.setattr(filter="data")` (already present for TAR at line 82), which restricts extraction, but this isn't explicitly validated.

**SVG to image conversion can produce transparent backgrounds unexpectedly:**
- Symptoms: SVG rasterization to PNG via cairosvg in `backend/converters/images.py` (line 86) always converts to RGBA, which may include transparency even if source SVG was opaque.
- Files: `backend/converters/images.py`
- Trigger: Convert an opaque SVG to PNG. Result may have unexpected alpha channel or transparent regions where user expected white/solid background.
- Workaround: Users can convert PNG→JPG (which strips alpha) if solid background is critical.

**Pydub audio format detection is unreliable for AAC/M4A:**
- Symptoms: `AudioSegment.from_file()` at line 202 in `/backend/converters/audio.py` uses format hints but may misidentify AAC vs M4A since both use similar codecs.
- Files: `backend/converters/audio.py`
- Trigger: An AAC file with wrong extension could be mislabeled during probing, leading to incorrect bitrate selection.
- Workaround: File extension-based detection (using `read_fmt` at line 197) is used as primary hint, so typically correct if extension matches.

**Pandas JSON normalization fails on nested structures:**
- Symptoms: `pd.json_normalize()` in `backend/converters/data.py` (line 87) flattens nested JSON objects into flat columns with dot notation (e.g., `{"user": {"name": "John"}}` → `{"user.name": "John"}`). Not reversible.
- Files: `backend/converters/data.py`
- Trigger: Convert a nested JSON to CSV and back to JSON. Structure is lost; nested objects become flat key-value pairs.
- Workaround: None. Users should validate JSON→CSV→JSON round-trips don't lose structural information.

## Security Considerations

**Docker image exposes internal port publicly:**
- Risk: Docker Compose at `docker-compose.yml` line 8 maps port 8070 directly to host `"8070:8070"` without any reverse proxy or authentication layer in the base config.
- Files: `docker-compose.yml`
- Current mitigation: Nginx config (`nginx.conf`) exists but is not referenced in docker-compose. Users deploying via compose get direct FastAPI exposure.
- Recommendations:
  1. Update docker-compose to use nginx service as frontend (see `nginx.conf` for template).
  2. Add authentication layer (e.g., basic auth, JWT) if exposed to untrusted networks.
  3. Document secure deployment patterns in README.

**Secrets in GitHub Actions workflow:**
- Risk: Docker Hub username (`semal31`) is hardcoded in `.github/workflows/docker.yml` (line 24). Token is referenced via `${{ secrets.DOCKERHUB_TOKEN }}` (line 25), but username leaks the account.
- Files: `.github/workflows/docker.yml`
- Current mitigation: Token is properly secrets-protected.
- Recommendations:
  1. Consider using a service account or organization secrets for Docker Hub.
  2. Monitor DockerHub access logs for unauthorized pushes.
  3. Rotate token periodically.

**No rate limiting on file conversion endpoints:**
- Risk: `/api/convert` and `/api/bulk-convert` endpoints have no rate limiting. Attackers can spam conversion requests, exhausting CPU/disk.
- Files: `backend/main.py`
- Current mitigation: None.
- Recommendations:
  1. Add rate limiting middleware (e.g., slowapi for FastAPI) with per-IP or per-session limits.
  2. Add request size limits beyond just file size (e.g., max conversions per minute).
  3. Monitor API logs for abuse patterns.

**Temp directory location not configurable:**
- Risk: Temp files always write to system temp directory via `tempfile.mkdtemp()` at line 40 in `backend/main.py`. No environment variable override.
- Files: `backend/main.py`
- Current mitigation: Files are cleaned up after 1 hour TTL.
- Recommendations:
  1. Allow `TEMP_DIR` or similar env var to configure location (e.g., for mounted volumes in Docker).
  2. Use a dedicated temp volume mounted at a known path for better lifecycle management and metrics.

**No input sanitization for format strings:**
- Risk: User-supplied `target_format` is used in logging (e.g., line 182 in `backend/main.py`). If format is crafted with format string characters, could cause issues in some logging frameworks.
- Files: `backend/main.py`
- Current mitigation: Python `logging` module isn't vulnerable to format string attacks in typical usage, but downstream tools (ffmpeg, pandoc) could misbehave.
- Recommendations:
  1. Whitelist allowed format strings (already done via `get_available_formats()` lookup).
  2. Never pass user input directly to subprocess commands (currently safe via ffmpeg-python API, not shell invocation).

## Performance Bottlenecks

**Video to GIF conversion uses two-pass encoding:**
- Problem: `_to_gif()` in `/backend/converters/video.py` (lines 179-249) always runs two ffmpeg passes (palette generation + encoding). This is slow for large videos.
- Files: `backend/converters/video.py`
- Cause: Two-pass is the best quality approach but is ~2x slower than single-pass. No option for faster single-pass mode.
- Improvement path:
  1. Add a `fast` quality option that uses single-pass or lower fps.
  2. Cache generated palettes for repeated GIF conversions of same video.
  3. Parallelize palette generation if GPU is available.

**Audio bitrate probing via ffprobe on every conversion:**
- Problem: `_probe_bitrate_kbps()` in `backend/converters/audio.py` (lines 74-101) runs ffprobe for every conversion with `quality="original"`. FFprobe is slow (100-500ms per file).
- Files: `backend/converters/audio.py`
- Cause: Probing is per-conversion, not cached. Users converting the same file to multiple formats pay the probe cost each time.
- Improvement path:
  1. Cache probe results in the upload metadata (store in UPLOADS dict when file is first uploaded).
  2. Return bitrate in the `/api/upload` response so frontend can pass it explicitly on convert.
  3. Avoid re-probing on retries.

**Archive repacking extracts entire archive to disk:**
- Problem: `ArchiveConverter._pack()` in `backend/converters/archives.py` (lines 96-125) extracts source to temp directory, then repacks. No streaming. Very large archives (GB+) require 2x disk space.
- Files: `backend/converters/archives.py`
- Cause: Simpler implementation but inefficient for large files.
- Improvement path:
  1. Implement streaming unpack/repack for ZIP→TAR, TAR→ZIP (avoid intermediate extraction).
  2. Use temp disk efficiently (reuse already-extracted members when possible).
  3. Add progress reporting for long conversions.

**Pandas reads entire CSV/XLSX into memory:**
- Problem: `_load()` in `backend/converters/data.py` (lines 71-96) uses `pd.read_csv()` and `pd.read_excel()` which load full files into memory. Large data files (100MB+) exhaust RAM.
- Files: `backend/converters/data.py`
- Cause: Pandas loads everything eagerly. No chunking option used.
- Improvement path:
  1. Add `chunksize` parameter for CSV reading: `pd.read_csv(path, chunksize=10000)`.
  2. Stream large files instead of converting in one go.
  3. Set a data file size limit (e.g., max 100MB) and reject larger files.

**Synchronous blocking converters in async context:**
- Problem: All converters run synchronously via `loop.run_in_executor()` at lines like 70 in `backend/converters/images.py`. If many users convert simultaneously, executor thread pool can become exhausted.
- Files: All converter modules use `run_in_executor()`
- Cause: Converters (ffmpeg, pandoc, Pillow) are blocking. Thread pool has limited workers (default ~5-10).
- Improvement path:
  1. Add explicit `max_workers` config to executor pool.
  2. Implement queue + priority system for conversion requests (e.g., smaller files first).
  3. Add request timeout to fail fast if conversion hangs.

## Fragile Areas

**Format detection relies solely on file extension:**
- Files: `backend/converters/__init__.py` (lines 41-65)
- Why fragile: `detect_format()` uses only file extension, not MIME type or file content. Users can rename `.mp3` to `.wav` and upload it, and the system will trust the extension.
- Safe modification: Add optional MIME type validation as secondary check. For critical formats (ZIP/TAR), verify file magic bytes.
- Test coverage: No unit tests for format detection; only tested via integration.

**Converter registry is global and instantiated once:**
- Files: `backend/converters/__init__.py` (lines 20-27)
- Why fragile: Each converter is a singleton instance. State (if any) is shared across all requests. Changing converter behavior or mocking for tests is difficult.
- Safe modification: Make converters stateless (already mostly true) or use factory pattern. Add explicit init/reset hooks.
- Test coverage: No unit tests for converter dispatch; only integration tests possible.

**Video codec selection hardcoded:**
- Files: `backend/converters/video.py` (lines 37-43 and 143-159)
- Why fragile: Codec choices (libx264 for MP4, mpeg4 for AVI) are hardcoded. If user has ffmpeg build without libx264, conversions fail with cryptic errors.
- Safe modification: Probe available codecs on startup and fail fast with helpful error message. Allow codec override via config.
- Test coverage: No tests verify codec availability; would fail only at runtime.

**PDF input not supported (pandoc limitation):**
- Files: `backend/converters/documents.py` (line 52)
- Why fragile: `get_output_formats()` returns empty list for PDF input (line 52). User uploads PDF expecting conversion options but gets empty array. No explanation in API.
- Safe modification: Add explicit error message in `/api/upload` response indicating PDF is output-only with explanation.
- Test coverage: No tests verify error messaging for unsupported conversions.

**Dynamic import of heavy libraries in converters:**
- Files: All converter modules import libraries inside functions (e.g., line 82 in `images.py`, line 77 in `documents.py`)
- Why fragile: Imports fail silently on first use, not on startup. Missing library (e.g., cairosvg) isn't detected until user tries SVG→PNG conversion.
- Safe modification: Move all imports to top-level and fail fast on startup if dependencies are missing. Add health checks.
- Test coverage: No startup tests verify all dependencies are installed.

## Scaling Limits

**In-memory upload/download tracking:**
- Current capacity: Hundreds of concurrent uploads/downloads limited by available RAM (dict size depends on metadata size, ~1KB per file = 1000 files per MB).
- Limit: Default Python limits on dict size. In typical VM (1GB RAM), can handle ~1M files before running out of memory. Real limit is much lower due to other app memory usage.
- Scaling path: Migrate to database (PostgreSQL, MongoDB) for unlimited file tracking. Use Redis for in-memory caching of active conversions.

**Single-threaded temp directory cleanup:**
- Current capacity: Cleanup task processes all expired files in one loop iteration. With 10k files to cleanup, takes several seconds.
- Limit: Under high concurrency, cleanup falls behind and temp directory grows unbounded.
- Scaling path: Use async cleanup loop or offload to background job queue (Celery, RQ). Add metrics/alerts for temp directory size.

**Synchronous executor thread pool:**
- Current capacity: Default executor pool has ~5-10 worker threads. Each conversion uses 1 thread for full duration (seconds to minutes depending on file size/codec).
- Limit: After 5-10 simultaneous conversions, new requests queue up. With 100 concurrent users, response times degrade badly.
- Scaling path: Increase `max_workers` (with memory trade-off). Better: implement async converters or use separate Celery workers for CPU-intensive tasks.

**Temp directory on single disk:**
- Current capacity: Depends on available disk space. Typical Docker environment with 10GB allocated can store ~100 large video files concurrently.
- Limit: Fills up under high concurrency. Cleanup loop can't keep up with incoming conversions.
- Scaling path: Mount separate volume for temp files with auto-expansion (Docker volumes, K8s PersistentVolumes). Implement tiered storage (hot temp → cold archive).

**FFmpeg/Pandoc process spawning:**
- Current capacity: Each conversion spawns 1-2 external processes (ffmpeg, ffprobe, pandoc, etc.). With 10 concurrent conversions, 10+ processes run.
- Limit: OS process limits (ulimit, systemd service limits). CPU bottleneck on multi-core systems.
- Scaling path: Use process pooling libraries (process_pool instead of thread pool for CPU-bound work). Implement conversion queue with priority.

## Dependencies at Risk

**py7zr (7z support):**
- Risk: Relatively obscure library. Less maintained than zipfile/tarfile. 7z format is proprietary (LZMA compression).
- Impact: If py7zr breaks or is abandoned, 7Z support disappears. Users relying on 7Z conversions cannot upgrade.
- Migration plan: Consider marking 7Z as "experimental" or deprecated. Fallback to storing 7Z files as ZIP. Alternatively, shell out to system `7z` binary instead of using Python library.

**weasyprint (HTML→PDF):**
- Risk: Depends on heavy system libraries (cairo, pango). Complex dependency graph. Documentation shows breaking changes between minor versions.
- Impact: Upgrade to new version can break HTML→PDF pipeline. Docker image bloat (cairo, pango, fonts add 200MB+).
- Migration plan:
  1. Pin versions explicitly in requirements (currently only `>=61.0`).
  2. Test new versions in CI before deploying.
  3. Consider alternatives (e.g., headless Chrome/Puppeteer, but adds different risk).

**cairosvg (SVG rasterization):**
- Risk: Depends on cairo. SVG spec is complex; edge cases in rendering vs browser behavior. Few active maintainers.
- Impact: If cairosvg breaks, SVG→PNG conversions fail. SVG rendering differences vs browser may surprise users.
- Migration plan: Add rendering option to use headless browser (Puppeteer/Playwright) for more accurate SVG→PNG. Document differences.

**ffmpeg-python wrapper:**
- Risk: Thin wrapper around ffmpeg binary. If ffmpeg API changes or binary not found, cryptic errors.
- Impact: Version mismatches between library expectations and system ffmpeg can cause silent failures.
- Migration plan: Consider moving to `subprocess` calls directly (loses some abstraction but gains control). Add version checks on startup.

**pandas:**
- Risk: Heavy dependency with large binary size. Many sub-dependencies. Major version changes can introduce breaking changes.
- Impact: Data conversions could break on upgrade. Docker image gets larger.
- Migration plan: For simple CSV/XLSX, consider lighter alternatives (csv module, openpyxl only). Current usage is mostly CSV/XLSX, so pandas could be optional.

**pypandoc (document conversion):**
- Risk: Wraps system pandoc binary. If pandoc not installed or version mismatch, conversions fail.
- Impact: Document conversions (DOCX→PDF, MD→HTML) completely blocked if pandoc is missing or wrong version.
- Migration plan: Add explicit pandoc version check on startup. Provide clear error message and installation instructions if missing.

## Missing Critical Features

**No conversion progress reporting:**
- Problem: Large file conversions (video transcoding, archive repacking) can take minutes. User has no feedback on progress.
- Blocks: Cannot show progress bar to user. Cannot estimate time to completion.

**No ability to cancel in-flight conversions:**
- Problem: Once `/api/convert` is called, no way to stop it. If user changes mind or process hangs, they must wait or kill server.
- Blocks: User experience is poor for long conversions. Wasted CPU cycles.

**No conversion history or resume:**
- Problem: No persistent record of conversions. If user closes browser and comes back, no way to see what they uploaded/converted.
- Blocks: Enterprise/batch use cases where audit trail is critical. Users must re-upload files if session expires.

**No support for custom quality parameters per format:**
- Problem: Quality parameter (original/high/medium/low/lossless) is global for bulk convert. Cannot request different quality for different file pairs.
- Blocks: Advanced workflows where different files need different quality settings.

**No conversion presets or templates:**
- Problem: Users must manually select target format for each file. No way to save "MP3 high quality" preset and apply to multiple files.
- Blocks: Batch operations where same conversion is applied to many files.

**No API authentication or user accounts:**
- Problem: Anyone with network access can use the converter. No way to restrict access or track usage per user.
- Blocks: Multi-tenant deployments. Usage analytics per user. Quota enforcement.

## Test Coverage Gaps

**Format detection edge cases:**
- What's not tested: Double extensions (e.g., `.tar.gz` detection), case sensitivity, filenames with no extension, filenames with multiple dots.
- Files: `backend/converters/__init__.py`
- Risk: Users upload `.TAR.GZ` (uppercase) and it fails silently or misdetects format.
- Priority: High

**Converter error conditions:**
- What's not tested: Malformed input files, corrupted archives, truncated images. Converters assume well-formed input.
- Files: All converter modules
- Risk: Converter crashes with unhelpful error message instead of gracefully handling bad input.
- Priority: High

**Concurrent file operations:**
- What's not tested: Race conditions in file creation, cleanup, or download. Multiple users uploading same filename simultaneously.
- Files: `backend/main.py`
- Risk: File collisions, leaked temp files, or corruption under high concurrency.
- Priority: Medium

**Bulk convert failure modes:**
- What's not tested: What happens if 1 out of 100 conversions fails. Partial ZIP creation, response accuracy.
- Files: `backend/main.py` (lines 269-351)
- Risk: ZIP contains only partially completed files. Error reporting is inaccurate.
- Priority: Medium

**Archive path traversal:**
- What's not tested: TAR archives with path traversal (`../../../etc/passwd`). ZIP path escape check tested, but TAR is not.
- Files: `backend/converters/archives.py`
- Risk: Security issue if filter="data" is not enforced on all platforms.
- Priority: High

**External binary availability:**
- What's not tested: Behavior when system binaries (ffmpeg, pandoc, etc.) are missing or wrong version.
- Files: All converter modules
- Risk: Cryptic errors on first conversion attempt. No feedback during startup.
- Priority: Medium

**Frontend API error handling:**
- What's not tested: Network failures, timeout handling, malformed API responses from backend.
- Files: `frontend/index.html`
- Risk: Frontend freezes or shows generic "error" when API is down or slow.
- Priority: Medium

---

*Concerns audit: 2026-02-24*
