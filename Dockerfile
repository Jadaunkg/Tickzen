# TickZen Flask Application - Cloud Run Dockerfile
# Multi-stage build to keep gcc/g++ out of the final image

# ============ Stage 1: Build dependencies ============
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for compiling C extensions (prophet, scipy, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements for caching
COPY requirements-cloudrun.txt ./

# Install Python packages into a prefix we can copy later
RUN pip install --no-cache-dir --prefix=/install -r requirements-cloudrun.txt

# ============ Stage 2: Final runtime image ============
FROM python:3.11-slim

WORKDIR /app

# Install only runtime system libs (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (no gcc/g++ in final image)
COPY --from=builder /install /usr/local

# Copy application code (filtered by .dockerignore)
COPY . .

# Create necessary runtime directories
RUN mkdir -p generated_data/temp_uploads \
    generated_data/stock_reports \
    logs

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Expose port
EXPOSE 8080

# Run with Gunicorn — optimized for Cloud Run
CMD exec gunicorn \
    --bind :$PORT \
    --workers 1 \
    --threads 8 \
    --timeout 300 \
    --worker-class gthread \
    --worker-tmp-dir /dev/shm \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    wsgi:application

