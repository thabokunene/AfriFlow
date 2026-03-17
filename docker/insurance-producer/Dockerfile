# Dockerfile for AfriFlow Insurance Kafka Producer
# Multi-stage build for production deployment

# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Production
# ============================================================================
FROM python:3.11-slim as production

WORKDIR /app

# Labels
LABEL maintainer="Thabo Kunene"
LABEL description="AfriFlow Insurance Kafka Producer"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd -r afriflow && useradd -r -g afriflow afriflow

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY afriflow/ ./afriflow/

# Copy configuration
COPY docker/ ./docker/

# Set ownership
RUN chown -R afriflow:afriflow /app

# Switch to non-root user
USER afriflow

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from afriflow.domains.insurance.ingestion.kafka_producer import InsuranceKafkaProducer; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "afriflow.domains.insurance.ingestion.kafka_producer"]

# ============================================================================
# Stage 3: Development
# ============================================================================
FROM production as development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy test files
COPY afriflow/tests/ ./afriflow/tests/

# Switch back to non-root user
USER afriflow

# Default command for development
CMD ["pytest", "afriflow/tests/unit/insurance/", "-v"]
