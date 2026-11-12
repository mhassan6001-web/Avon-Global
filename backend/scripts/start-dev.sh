#!/bin/sh
# Development only: apply migrations, then start the API with auto-reload.
set -eu
echo "Applying database migrations..."
alembic upgrade head
python -m app.cli sync-catalogue
echo "Starting AVEN GLOBAL API (development)..."
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
