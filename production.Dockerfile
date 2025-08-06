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
RUN chmod +x /usr/local/bin/mscore4
RUN mkdir -p /home/appuser/.local/share/MuseScore/MuseScore4/logs && \
    chown -R appuser:appuser /home/appuser/.local

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist /var/www/html

# Copy Nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Install netcat for database health checks
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Set proper permissions
RUN chown -R appuser:appuser /app /var/www/html && \
    # Create nginx directories and set permissions
    mkdir -p /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx && \
    chown -R appuser:appuser /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx && \
    # Allow nginx to bind to port 80
    chmod 755 /var/log/nginx

WORKDIR /app/backend

# Don't switch to non-root user yet - nginx needs root privileges
# USER appuser

EXPOSE 80

# Create entrypoint script inline and run it
CMD ["bash", "-c", "\
    echo '[INFO] Starting application initialization...' && \
    DB_HOST=${POSTGRES_HOST:-db} && \
    DB_PORT=${POSTGRES_PORT:-5432} && \
    echo '[INFO] Waiting for database connection...' && \
    while ! nc -z $DB_HOST $DB_PORT; do \
        echo '[WARN] Database unavailable - waiting...' && \
        sleep 2; \
    done && \
    echo '[INFO] Database is ready!' && \
    echo '[INFO] Running Django migrations...' && \
    su -c 'python manage.py migrate --noinput' appuser && \
    echo '[INFO] Collecting static files...' && \
    su -c 'python manage.py collectstatic --noinput' appuser && \
    echo '[INFO] Starting Gunicorn...' && \
    su -c 'gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile -' appuser & \
    echo '[INFO] Starting Celery worker...' && \
    su -c 'celery -A backend worker --loglevel=info' appuser & \
    sleep 3 && \
    echo '[INFO] Starting Nginx...' && \
    nginx -t && \
    exec nginx -g 'daemon off;' \
"]