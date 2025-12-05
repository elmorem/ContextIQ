# Sessions Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from service directory
COPY services/sessions/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules and service code
COPY shared/ /app/shared/
COPY services/sessions/ /app/services/sessions/

# Set Python path to include shared modules
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health/live')"

# Run application
CMD ["uvicorn", "services.sessions.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
