# =============================================================================
# SERV.O Mail Monitor - Dockerfile
# =============================================================================

FROM python:3.11-slim

WORKDIR /mail_monitor

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /mail_monitor/temp /mail_monitor/logs /mail_monitor/data

# Database dependencies (psycopg2 for email_db.py)
RUN pip install --no-cache-dir psycopg2-binary

CMD ["python", "scheduler.py"]
