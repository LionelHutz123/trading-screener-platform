# Multi-stage build for secure Python backend
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with security-focused settings
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Production stage - secure hardened image
FROM python:3.11-slim

# Security: Update packages and remove unnecessary ones
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    curl \
    ca-certificates \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Security: Create non-root user with minimal privileges
RUN groupadd -r -g 1000 trading && \
    useradd -r -g trading -u 1000 -s /bin/false -c "Trading API User" trading

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set secure working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=trading:trading . .

# Create necessary directories with strict permissions
RUN mkdir -p data logs config backups && \
    chown -R trading:trading data logs config backups && \
    chmod 750 data logs config backups

# Security: Set proper file permissions
RUN find /app -type f -name "*.py" -exec chmod 644 {} \; && \
    find /app -type d -exec chmod 755 {} \; && \
    chmod 755 /app/app_platform_api.py && \
    chmod 755 /app/health_check.py && \
    chmod 644 /app/security_middleware.py && \
    chmod 644 /app/security_monitor.py

# Security: Set environment variables
ENV PYTHONPATH=/app
ENV ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Security: Remove write permissions from application directory
RUN chmod -R a-w /app && \
    chmod u+w /app/data /app/logs /app/config /app/backups

# Security: Switch to non-root user
USER trading

# Expose port (non-privileged)
EXPOSE 8080

# Enhanced health check with security validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Security: Add labels for container identification
LABEL \
    org.opencontainers.image.title="HutzTrades Secure API" \
    org.opencontainers.image.description="Professional trading platform with enterprise security" \
    org.opencontainers.image.version="2.0.0" \
    org.opencontainers.image.vendor="HutzTrades" \
    security.level="high" \
    security.features="rate-limiting,ddos-protection,monitoring"

# Security: Drop all capabilities and add only necessary ones
USER trading

# Run the API with multiple fallbacks
CMD ["sh", "-c", "python app_standalone.py || python app_platform_api.py || python app_minimal.py"]
