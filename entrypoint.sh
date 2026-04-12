#!/bin/sh
# Fix volume permissions (Railway mounts volumes as root)
chown -R agentforge:agentforge /app/data 2>/dev/null || true

# Drop to app user and start the server
exec su -s /bin/sh agentforge -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"
