# ==============================================================================
# Multi-stage production Dockerfile for Speech-to-Text Microservice
# ==============================================================================

FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


# ------------------------------------------------------------------------------
# Final Runtime Stage
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies: ffmpeg, ffprobe, and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user and temporary working directory
RUN useradd -u 1001 -m -s /bin/bash appuser && \
    mkdir -p /tmp/stt /home/appuser/.cache && \
    chown -R appuser:appuser /tmp/stt /app /home/appuser

# Copy application source code
COPY --chown=appuser:appuser app/ ./app/

# Switch to non-root user for security hardening
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=5001 \
    TEMP_DIR=/tmp/stt \
    HOME=/home/appuser

EXPOSE 5001

# Healthcheck checking /stt-api/v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/stt-api/v1/health || exit 1

# Start service via Uvicorn (single worker to prevent duplicated model memory footprint)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
