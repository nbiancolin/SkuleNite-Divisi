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
        netcat-traditional \
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

# Add this before the CMD instruction
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# # Change the CMD to:
# CMD ["start.sh"]

# RUN chmod +x /start.sh

# Set proper permissions
RUN chown -R appuser:appuser /app /var/www/html /var/log/nginx /var/lib/nginx /etc/nginx

WORKDIR /app/backend

# Switch to non-root user
USER appuser

EXPOSE 80

CMD ["start.sh"]