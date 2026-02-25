FROM python:3.12-slim-bookworm

# Ensure UTF-8 locale for non-ASCII filenames and subprocess arguments
# (base image already sets this, but explicit is more resilient)
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# System dependencies for all converters
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    ffmpeg \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto-core \
    curl \
    gosu \
    tzdata

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build-time smoke test: fail immediately if WeasyPrint cannot import its
# system dependencies. A broken image must not be pushed.
RUN python -c "import weasyprint; print('weasyprint import OK')"

COPY backend/ .
COPY frontend/ /app/frontend/

# Persistent data directory for uploads and conversions
RUN mkdir -p /app/data
VOLUME /app/data

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# OCI labels
LABEL org.opencontainers.image.title="File Converter" \
      org.opencontainers.image.description="Self-hosted file conversion tool — documents, images, audio, video, data, archives" \
      org.opencontainers.image.source="https://github.com/semal31/file-converter" \
      org.opencontainers.image.version="1.0.0"

ENV PORT=8070
ENV PUID=99
ENV PGID=100
EXPOSE 8070

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
