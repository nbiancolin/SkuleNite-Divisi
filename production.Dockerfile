# ==========================================
# 1. FRONTEND BUILD STAGE
# ==========================================
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./

# Use npm ci with proper flags for build stage
RUN npm ci --include=optional --fund=false --audit=false

# Copy source and build
COPY frontend/ .
RUN npm run build

# ==========================================
# 2. BACKEND BUILD STAGE
# ==========================================
FROM python:3.11-slim AS backend-build

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen

WORKDIR /app/backend

# Install system dependencies in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        curl \
        fontconfig \
        unzip \
        xdg-utils \
        ca-certificates \
        libglib2.0-0 \
        libfuse2 \
        libasound2 \
        libjack0 \
        libnss3 \
        libopengl0 \
        libgl1 \
        libglx0 \
        libegl1 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libsm6 \
        libice6 \
        libxrandr2 \
        libxinerama1 \
        libxcursor1 \
        libxi6 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxss1 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libxkbcommon-x11-0 \
        libxcb1 \
        qt5dxcb-plugin \
        p7zip-full && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Install MuseScore 4
ENV MSCORE_VERSION=4.5.2.251141401
ENV MSCORE_APPIMAGE=MuseScore-Studio-${MSCORE_VERSION}-x86_64.AppImage

RUN wget -O /tmp/mscore.AppImage "https://cdn.jsdelivr.net/musescore/v4.5.2/${MSCORE_APPIMAGE}" && \
    chmod +x /tmp/mscore.AppImage && \
    cd /tmp && \
    ./mscore.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore && \
    ln -s /opt/musescore/AppRun /usr/local/bin/mscore4 && \
    rm /tmp/mscore.AppImage

# Install custom fonts
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# ==========================================
# 3. FINAL PRODUCTION STAGE
# ==========================================
FROM python:3.11-slim AS production

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gettext \
        nginx \
        curl \
        bash \
        wait-for-it \
        fontconfig \
        ca-certificates \
        libglib2.0-0 \
        libfuse2 \
        libasound2 \
        libjack0 \
        libnss3 \
        libopengl0 \
        libgl1 \
        libglx0 \
        libegl1 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libsm6 \
        libice6 \
        libxrandr2 \
        libxinerama1 \
        libxcursor1 \
        libxi6 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxss1 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libxkbcommon-x11-0 \
        libxcb1 \
        qt5dxcb-plugin \
        p7zip-full && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

# Copy Python dependencies from build stage
COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

# Copy backend application
COPY --from=backend-build /app/backend /app/backend

# Copy fonts and MuseScore
COPY --from=backend-build /usr/share/fonts /usr/share/fonts
COPY --from=backend-build /opt/musescore /opt/musescore
RUN ln -sf /opt/musescore/AppRun /usr/local/bin/mscore4

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist /var/www/html

# Copy Nginx config and create start script
COPY nginx.conf /etc/nginx/nginx.conf

# Create start script directly in Dockerfile
RUN cat > /start.sh << 'EOF'
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
    
    DB_HOST=${DATABASE_HOST:-db}
    DB_PORT=${DATABASE_PORT:-5432}
    
    while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
        log_warn "Database is unavailable - waiting 2 seconds..."
        sleep 2
    done
    
    log_info "Database is ready!"
    
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
    
    log_info "Starting Celery worker..."
    celery -A backend worker \
        --loglevel=info \
        --concurrency=2 \
        --max-tasks-per-child=1000 &
    
    CELERY_PID=$!
    
    sleep 3
    
    if ! kill -0 $GUNICORN_PID 2>/dev/null; then
        log_error "Gunicorn failed to start"
        exit 1
    fi
    
    if ! kill -0 $CELERY_PID 2>/dev/null; then
        log_error "Celery failed to start"
        exit 1
    fi
    
    log_info "Application services started successfully!"
}

# Main execution
log_info "Starting application initialization..."
wait_for_db
run_migrations
collect_static
start_services

log_info "Starting Nginx..."
if nginx -t; then
    log_info "Nginx configuration is valid"
else
    log_error "Nginx configuration is invalid"
    exit 1
fi

exec nginx -g "daemon off;"
EOF

RUN chmod +x /start.sh

# Set proper permissions
RUN chown -R appuser:appuser /app /var/www/html /var/log/nginx /var/lib/nginx /etc/nginx

WORKDIR /app/backend

# Switch to non-root user
USER appuser

EXPOSE 80

CMD ["/start.sh"]