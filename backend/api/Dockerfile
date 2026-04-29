# Build context: ./backend (so we can COPY both api/ and shared/)
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install API service dependencies
COPY api/requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt

# Copy the shared package as a plain directory next to app/
COPY shared /srv/shared

# Copy the API application code
COPY api/app /srv/app

# Non-root user
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /srv
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]