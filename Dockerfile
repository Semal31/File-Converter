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
    curl

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build-time smoke test: fail immediately if WeasyPrint cannot import its
# system dependencies. A broken image must not be pushed.
RUN python -c "import weasyprint; print('weasyprint import OK')"

COPY backend/ .
COPY frontend/ /app/frontend/

ENV PORT=8070
EXPOSE 8070

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
