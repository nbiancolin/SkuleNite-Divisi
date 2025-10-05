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
        libgpg-error0 \ 
        p7zip-full \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Install MuseScore 4
ENV MSCORE_SMALL_VERSION=4.6.0
ENV MSCORE_VERSION=4.6.0.252730944
ENV MSCORE_APPIMAGE=MuseScore-Studio-${MSCORE_VERSION}-x86_64.AppImage

RUN wget -O /tmp/mscore.AppImage "https://cdn.jsdelivr.net/musescore/v${MSCORE_SMALL_VERSION}/${MSCORE_APPIMAGE}" && \
    chmod +x /tmp/mscore.AppImage && \
    cd /tmp && \
    ./mscore.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore && \
    ln -s /opt/musescore/AppRun /usr/local/bin/mscore4 && \
    rm /tmp/mscore.AppImage

# Install custom fonts PROPERLY
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    # Set proper permissions for fonts
    chmod -R 644 /usr/share/fonts/truetype/custom/*.ttf /usr/share/fonts/truetype/custom/*.otf 2>/dev/null || true && \
    chmod -R 644 /usr/share/fonts/truetype/custom/*.TTF /usr/share/fonts/truetype/custom/*.OTF 2>/dev/null || true && \
    chmod 755 /usr/share/fonts/truetype/custom && \
    # Update font cache
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

# Create non-root user early
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies including essential fonts
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
        libgpg-error0 \ 
        p7zip-full \
        netcat-openbsd \
        xvfb \
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
COPY --from=backend-build /app/backend /app/backend

# Copy fonts from build stage with proper ownership
COPY --from=backend-build --chown=root:root /usr/share/fonts /usr/share/fonts

# Copy MuseScore from build stage
COPY --from=backend-build /opt/musescore /opt/musescore
RUN ln -sf /opt/musescore/AppRun /usr/local/bin/mscore4 && \
    chmod +x /usr/local/bin/mscore4

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

WORKDIR /app/backend

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
    su -c 'mscore4 --help > /dev/null 2>&1 || echo \"[WARN] MuseScore may have issues but continuing...\"' appuser && \
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