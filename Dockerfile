# Pin the base image to a specific patch tag so rebuilds are reproducible and a
# scanner can pin known CVEs to a known digest.
FROM python:3.11.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# --no-install-recommends keeps the recommended-but-unneeded packages out of the
# image. Fewer packages is a smaller attack surface and fewer CVEs to triage.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Fail the container as unhealthy if the app stops serving.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status==200 else sys.exit(1)"

# Run the application. No --reload: it is a development-only file watcher that has
# no place in an image and widens the runtime surface.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
