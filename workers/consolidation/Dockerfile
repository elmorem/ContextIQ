# Consolidation Worker Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY workers/consolidation/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and worker code
COPY shared/ /app/shared/
COPY workers/consolidation/ /app/workers/consolidation/

# Set Python path to include shared modules
ENV PYTHONPATH=/app:$PYTHONPATH

# Health check (check if worker process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ps aux | grep -v grep | grep -q "python.*worker" || exit 1

# Run worker
CMD ["python", "-m", "workers.consolidation.worker"]
