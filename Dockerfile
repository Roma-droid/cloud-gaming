# Cloud Gaming Platform — Backend
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Application code
COPY backend/ backend/

# Non-root user
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
