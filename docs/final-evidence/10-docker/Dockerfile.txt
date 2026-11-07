# Production Dockerfile for Finance Tracker (Flask)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered console logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Install minimal OS security certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root system user and group for container security
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 -d /app -s /sbin/nologin appuser

# Install Python dependencies first for caching efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code with non-root ownership
COPY --chown=appuser:appuser . .

# Ensure uploads directory exists and is owned by appuser
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 5000

# Container healthcheck using Python's built-in urllib
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/').read()" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
