#!/bin/sh
set -e
alembic upgrade head
# Write the snapshot from the real database so an outage never falls back to placeholder content.
python -m app.snapshot || echo "start.sh: snapshot not written; continuing without one" >&2
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 2 \
  --proxy-headers --forwarded-allow-ips '*'
