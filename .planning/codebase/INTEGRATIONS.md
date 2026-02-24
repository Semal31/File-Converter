# External Integrations

**Analysis Date:** 2026-02-24

## APIs & External Services

**None Detected**

This application does not integrate with any external APIs or cloud services. All conversions are performed locally using open-source tools and libraries.

## Data Storage

**Databases:**
- Not used - No database integration

**File Storage:**
- Local filesystem only
  - Temporary directory: System `tempfile` with `fc_` prefix
  - Upload storage: In-memory metadata + temp disk files
  - Download storage: Converted files in temp disk storage
  - Expiration: 1 hour TTL (hardcoded) or on download, whichever comes first

**Caching:**
- None - No external caching service

## Authentication & Identity

**Auth Provider:**
- Not implemented - No user authentication
- CORS: Open to all origins (`allow_origins=["*"]`)
- No API keys, OAuth, or JWT required

**Access Control:**
- Public (no authentication layer)
- Single-tenant, self-hosted deployment model

## Monitoring & Observability

**Error Tracking:**
- Not integrated - No external error tracking service

**Logs:**
- Python stdlib logging to stdout
  - Format: `%(asctime)s %(levelname)s %(name)s: %(message)s`
  - Level: INFO (set in `backend/main.py`)
  - Modules: `fc.main`, `fc.documents`, `fc.images`, `fc.audio`, `fc.video`, `fc.archives`, `fc.data`
  - Output: Console (captured by Docker compose)

## CI/CD & Deployment

**Hosting:**
- Self-hosted via Docker (any Docker-capable server)
- Docker Hub registry: `semal31/file-converter` (push-only)

**CI Pipeline:**
- GitHub Actions
- Workflow: `.github/workflows/docker.yml`
- Trigger: Commits to `main` branch
- Build: Docker buildx
- Authentication: Docker Hub (via `DOCKERHUB_TOKEN` secret)
- Artifacts: Docker images tagged as:
  - `semal31/file-converter:latest`
  - `semal31/file-converter:${{ github.sha }}`

**Docker Image Tags:**
- Latest version: `semal31/file-converter:latest`
- Commit-based: `semal31/file-converter:<git-sha>`

## Environment Configuration

**Required env vars:**
- `PORT` (optional) - Server port for backend Uvicorn (default: 8070)
- No API keys or secrets required

**Secrets location:**
- GitHub Actions secret: `DOCKERHUB_TOKEN` (Docker Hub credentials)
- No application-level secrets in code

## Webhooks & Callbacks

**Incoming:**
- None - No incoming webhooks supported

**Outgoing:**
- None - No outgoing webhook integrations

## System Integration Points

**External Binaries (Wrapped, Not APIs):**
- Pandoc (document conversion engine)
  - Called via `pypandoc` library
  - Binary path: System PATH (no special config)

- FFmpeg (audio/video conversion engine)
  - Called via `pydub` and `ffmpeg-python` libraries
  - Binary path: System PATH (no special config)

**Supported File Formats (No API Dependencies):**
- All conversions are local, format-specific implementations
- No cloud storage APIs (S3, GCS, etc.)
- No format detection APIs

## Network Configuration

**Frontend (Nginx Proxy):**
- Port: 8071 (Docker production)
- API route: `/api/*` → proxied to `http://backend:8070/api/`
- SPA fallback: All non-API routes → `index.html`
- Timeout: 300s (5 minutes) for long conversions
- Max body size: 512MB

**Backend (Uvicorn/FastAPI):**
- Port: 8070 (internal to Docker, exposed in development)
- CORS: All origins allowed
- Health check endpoint: `GET /api/health`
- No rate limiting, authentication, or request validation beyond format checks

---

*Integration audit: 2026-02-24*
