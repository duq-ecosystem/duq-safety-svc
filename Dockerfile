# DUQ Safety Service Dockerfile
# Multi-stage build for minimal image size

# ============================================================================
# Build stage
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install pip and build tools
RUN pip install --no-cache-dir --upgrade pip wheel

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies
# Note: duq-agent-core is installed from git or local path
RUN pip install --no-cache-dir .

# ============================================================================
# Runtime stage
# ============================================================================
FROM python:3.11-slim AS runtime

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN groupadd -r safety && useradd -r -g safety safety

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /app/src /app/src

# Set ownership
RUN chown -R safety:safety /app

# Switch to non-root user
USER safety

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SAFETY_HOST=0.0.0.0 \
    SAFETY_PORT=8083 \
    LOG_LEVEL=INFO

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8083/health').raise_for_status()"

# Run application
CMD ["python", "-m", "duq_safety_svc.main"]
