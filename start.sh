#!/bin/bash
set -e

# Start Uvicorn in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Start Celery in background
celery -A app.core.celery_app.celery_app worker --loglevel=info &

# Wait for any process to exit
wait -n

# Exit with the status of the first process to fail
exit $?
