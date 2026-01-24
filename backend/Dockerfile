# =============================================================================
# SERV.O Backend - Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ .

# Copy mail_monitor module (same level as backend expects)
COPY mail_monitor/ /mail_monitor/

# Create directories for uploads, outputs, and mail_monitor
RUN mkdir -p /app/uploads /app/outputs /mail_monitor/temp /mail_monitor/logs /mail_monitor/data

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
