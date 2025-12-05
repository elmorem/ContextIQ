# Memory Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from service directory
COPY services/memory/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and service code
COPY shared/ /app/shared/
COPY services/memory/ /app/services/memory/

# Set Python path to include shared modules
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health/live')"

# Run application
CMD ["uvicorn", "services.memory.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
