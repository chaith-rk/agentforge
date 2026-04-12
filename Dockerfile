# Multi-stage Dockerfile for AgentForge Platform
# Stage 1: Build dependencies
# Stage 2: Slim runtime image

# --- Build Stage ---
FROM python:3.11-slim as builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime Stage ---
FROM python:3.11-slim

# Security: create non-root user (entrypoint drops to this user after fixing perms)
RUN groupadd -r agentforge && useradd -r -g agentforge -d /app -s /sbin/nologin agentforge

WORKDIR /app

# Copy installed dependencies from build stage
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY agents/ ./agents/
COPY prompts/ ./prompts/
COPY entrypoint.sh ./entrypoint.sh

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R agentforge:agentforge /app && chmod +x /app/entrypoint.sh

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",8000)}/health')" || exit 1

# Run as root initially so entrypoint can fix volume permissions, then drop to agentforge
CMD ["/app/entrypoint.sh"]
