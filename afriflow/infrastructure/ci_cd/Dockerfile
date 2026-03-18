# =============================================================================
# @file Dockerfile
# @description Multi-stage Docker image for the AfriFlow CI/CD runner and
#              application container. Stage 1 (builder) installs all Python
#              dependencies into a virtual environment. Stage 2 (runtime)
#              copies only the venv and application code, producing a lean
#              final image with no build-time tooling included.
# @author Thabo Kunene
# @created 2026-03-17
# =============================================================================

# ---------------------------------------------------------------------------
# STAGE 1: builder
# Uses the full Python slim image to compile native extensions (e.g. psycopg2,
# confluent-kafka) and resolve all pip dependencies into /opt/venv.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set a consistent working directory for all build steps
WORKDIR /build

# Install OS-level build dependencies required by certain Python packages:
#   build-essential — C compiler toolchain for native extensions
#   libpq-dev        — PostgreSQL headers needed by psycopg2
#   curl             — used in healthchecks and download steps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*    # Clean apt cache to keep layer small

# Create an isolated virtual environment so runtime stage can copy it cleanly
RUN python -m venv /opt/venv

# Ensure pip commands use the venv's pip, not the system pip
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency manifests first — Docker caches this layer until they change,
# avoiding a full pip install on every code-only change.
COPY afriflow/requirements.txt afriflow/requirements-dev.txt ./

# Install production dependencies; dev requirements are installed separately
# to allow test images to include them without polluting the prod image.
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# STAGE 2: runtime
# Starts from the same slim base — no build tools, smaller attack surface.
# Copies only the venv and application code from the builder stage.
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Metadata labels for image registry traceability
LABEL maintainer="Thabo Kunene" \
      project="AfriFlow" \
      version="1.0.0" \
      description="AfriFlow data platform application image"

# Install runtime-only OS packages (libpq for psycopg2 at runtime; curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the fully-built virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate the venv for all subsequent commands and at container start
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create a non-root user for security — never run application code as root
RUN groupadd --gid 1001 afriflow \
    && useradd --uid 1001 --gid afriflow --shell /bin/bash --create-home afriflow

# Set working directory for the application
WORKDIR /app

# Copy AfriFlow application source code into the image
COPY afriflow/ ./afriflow/

# Transfer ownership to the non-root user
RUN chown -R afriflow:afriflow /app

# Switch to non-root user for runtime
USER afriflow

# Expose no ports by default — specific services override this in their own
# Dockerfiles or via docker-compose port mappings.

# Default command runs the AfriFlow CLI entrypoint; override in compose or
# Kubernetes pod specs as needed.
CMD ["python", "-m", "afriflow"]
