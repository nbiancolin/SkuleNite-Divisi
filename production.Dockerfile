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

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for MuseScore
RUN apt-get update && apt-get install -y \
    # Build essentials for Python packages
    gcc \
    g++ \
    make \
    # Database clients
    postgresql-client \
    default-libmysqlclient-dev \
    # Dependencies for MuseScore 4
    wget \
    xvfb \
    xauth \
    libfuse2 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    # OpenGL/EGL libraries
    libopengl0 \
    libglx0 \
    libegl1 \
    libglu1-mesa \
    # Audio libraries
    libasound2 \
    libjack-jackd2-0 \
    # Font libraries
    fontconfig \
    libfontconfig1 \
    fonts-liberation \
    # GLib libraries
    libglib2.0-0 \
    # GPG libraries
    libgpg-error0 \
    # NSS libraries
    libnss3 \
    # Additional Qt/X11 dependencies
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-render-util0 \
    libxcb-randr0 \
    # Useful utilities
    curl \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install MuseScore 4 AppImage
RUN wget -O /tmp/MuseScore-4.AppImage https://github.com/musescore/MuseScore/releases/download/v4.6.2/MuseScore-Studio-4.6.2.252830930-x86_64.AppImage && \
    chmod +x /tmp/MuseScore-4.AppImage && \
    /tmp/MuseScore-4.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore && \
    rm /tmp/MuseScore-4.AppImage

# Create a wrapper script for MuseScore to work headless
RUN echo '#!/bin/bash\nxvfb-run -a /opt/musescore/AppRun "$@"' > /usr/local/bin/musescore && \
    chmod +x /usr/local/bin/musescore

# Copy and install custom fonts
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# Install Python dependencies
# Copy requirements first for better caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

# ==========================================
# 3. FINAL PRODUCTION STAGE
# ==========================================
FROM python:3.11-slim AS production

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=offscreen

# Create non-root user early
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies
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
        libjack-jackd2-0 \
        libnss3 \
        libopengl0 \
        libgl1 \
        libglx0 \
        libegl1 \
        libglu1-mesa \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libsm6 \
        libice6 \
        libxrandr2 \
        libxinerama1 \
        libxcb-xinerama0 \
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
        libxcb-cursor0 \
        libxcb-xfixes0 \
        libxcb-shape0 \
        libxcb-render-util0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libgpg-error0 \
        pipewire \
        p7zip-full \
        netcat-openbsd \
        xvfb \
        x11-xserver-utils \
        xauth \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto \
        fonts-freefont-ttf && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

WORKDIR /app

# Copy Python dependencies from build stage
COPY --from=backend-build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-build /usr/local/bin /usr/local/bin

# Copy backend application
COPY --from=backend-build /app /app

# Copy fonts from build stage with proper ownership
COPY --from=backend-build --chown=root:root /usr/share/fonts /usr/share/fonts

# Copy MuseScore from build stage
COPY --from=backend-build /opt/musescore /opt/musescore
COPY --from=backend-build /usr/local/bin/musescore /usr/local/bin/musescore
RUN chmod +x /usr/local/bin/musescore

# Create MuseScore directories with proper permissions
RUN mkdir -p /home/appuser/.local/share/MuseScore/MuseScore4/logs && \
    mkdir -p /home/appuser/.config/MuseScore && \
    chown -R appuser:appuser /home/appuser

# Create font cache directories with proper permissions
RUN mkdir -p /var/cache/fontconfig && \
    chmod 1777 /var/cache/fontconfig && \
    mkdir -p /tmp/fontconfig && \
    chmod 1777 /tmp/fontconfig && \
    # Create user-specific font directories
    mkdir -p /home/appuser/.cache/fontconfig && \
    mkdir -p /home/appuser/.fonts && \
    chown -R appuser:appuser /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser/.fonts

# Generate font cache as root first
RUN fc-cache -f -v

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist /var/www/html

# Copy Nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Set proper permissions for application files
RUN chown -R appuser:appuser /app /var/www/html && \
    # Create nginx directories and set permissions
    mkdir -p /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx && \
    chown -R appuser:appuser /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx && \
    chmod 755 /var/log/nginx

WORKDIR /app

EXPOSE 80

# Create entrypoint script with improved font handling
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
    echo '[INFO] Setting up fonts for appuser...' && \
    su -c 'fc-cache -f -v' appuser && \
    su -c 'fc-list | head -10' appuser && \
    echo '[INFO] Testing MuseScore font access...' && \
    su -c 'musescore --help > /dev/null 2>&1 || echo \"[WARN] MuseScore may have issues but continuing...\"]' appuser && \
    echo '[INFO] Running Django migrations...' && \
    su -c 'python manage.py migrate --noinput' appuser && \
    echo '[INFO] Setting up Music21 ... ' && \
    su -c 'python _scripts/setup_music21.py' appuser && \
    echo '[INFO] Collecting static files...' && \
    su -c 'python manage.py collectstatic --noinput' appuser && \
    echo '[INFO] Starting Gunicorn...' && \
    su -c 'FONTCONFIG_CACHE=/home/appuser/.cache/fontconfig gunicorn backend.wsgi:application --bind 0.0.0.0:8000 --workers 4 --timeout 120 --access-logfile - --error-logfile -' appuser & \
    echo '[INFO] Starting Celery worker...' && \
    su -c 'FONTCONFIG_CACHE=/home/appuser/.cache/fontconfig celery -A backend worker --loglevel=info' appuser & \
    sleep 3 && \
    echo '[INFO] Starting Nginx...' && \
    nginx -t && \
    exec nginx -g 'daemon off;' \
"]