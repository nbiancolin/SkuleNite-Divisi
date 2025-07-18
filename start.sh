#!/bin/bash
set -e

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 &

# Start Celery worker
echo "Starting Celery..."
celery -A backend worker --loglevel=info &

# Start Celery beat (optional)
# celery -A backend beat --loglevel=info &

# Start Nginx in the foreground
echo "Starting Nginx..."
nginx -g "daemon off;"
