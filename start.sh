#!/bin/bash
set -e

# Colors for better logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for database
wait_for_db() {
    log_info "Waiting for database connection..."
    
    # Extract database info from Django settings or environment variables
    DB_HOST=${POSTGRES_HOST:-db}
    DB_PORT=${POSTGRES_PORT:-5432}
    
    # Wait for database to be ready
    while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
        log_warn "Database is unavailable - waiting 2 seconds..."
        sleep 2
    done
    
    log_info "Database is ready!"
    
    # Additional check: try to connect with Django
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Attempting database connection (attempt $attempt/$max_attempts)..."
        
        if python manage.py check --database default; then
            log_info "Database connection successful!"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                log_error "Failed to connect to database after $max_attempts attempts"
                exit 1
            fi
            log_warn "Database connection failed, retrying in 3 seconds..."
            sleep 3
            attempt=$((attempt + 1))
        fi
    done
}

# Function to run migrations with retry
run_migrations() {
    log_info "Running Django migrations..."
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python manage.py migrate --noinput; then
            log_info "Migrations completed successfully!"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                log_error "Migrations failed after $max_attempts attempts"
                exit 1
            fi
            log_warn "Migration attempt $attempt failed, retrying in 5 seconds..."
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
}

# Function to collect static files
collect_static() {
    log_info "Collecting static files..."
    if python manage.py collectstatic --noinput; then
        log_info "Static files collected successfully!"
    else
        log_error "Failed to collect static files"
        exit 1
    fi
}

# Function to start services
start_services() {
    log_info "Starting application services..."
    
    # Start Gunicorn in background
    log_info "Starting Gunicorn..."
    gunicorn backend.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 4 \
        --timeout 120 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --access-logfile - \
        --error-logfile - &
    
    GUNICORN_PID=$!
    
    # Start Celery worker in background
    log_info "Starting Celery worker..."
    celery -A backend worker \
        --loglevel=info \
        --concurrency=2 \
        --max-tasks-per-child=1000 &
    
    CELERY_PID=$!
    
    # Optional: Start Celery beat
    # log_info "Starting Celery beat..."
    # celery -A backend beat --loglevel=info &
    # CELERY_BEAT_PID=$!
    
    # Wait a moment for services to start
    sleep 3
    
    # Check if Gunicorn is still running
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        log_error "Gunicorn failed to start"
        exit 1
    fi
    
    # Check if Celery is still running
    if ! kill -0 $CELERY_PID 2>/dev/null; then
        log_error "Celery failed to start"
        exit 1
    fi
    
    log_info "Application services started successfully!"
}

# Function to start nginx
start_nginx() {
    log_info "Starting Nginx..."
    
    # Test nginx configuration first
    if nginx -t; then
        log_info "Nginx configuration is valid"
    else
        log_error "Nginx configuration is invalid"
        exit 1
    fi
    
    # Start nginx in foreground
    exec nginx -g "daemon off;"
}

# Function to handle shutdown gracefully
cleanup() {
    log_info "Shutting down services..."
    
    # Kill background processes
    if [ ! -z "$GUNICORN_PID" ] && kill -0 $GUNICORN_PID 2>/dev/null; then
        log_info "Stopping Gunicorn..."
        kill -TERM $GUNICORN_PID
        wait $GUNICORN_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$CELERY_PID" ] && kill -0 $CELERY_PID 2>/dev/null; then
        log_info "Stopping Celery..."
        kill -TERM $CELERY_PID
        wait $CELERY_PID 2>/dev/null || true
    fi
    
    log_info "Services stopped"
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main execution
main() {
    log_info "Starting application initialization..."
    
    # Wait for database to be ready
    wait_for_db
    
    # Run migrations
    run_migrations
    
    # Collect static files
    collect_static
    
    # Start application services
    start_services
    
    # Start nginx (this will run in foreground)
    start_nginx
}

# Run main function
main "$@"