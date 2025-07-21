# ==========================================
# 1. FRONTEND BUILD STAGE
# ==========================================
FROM node:20 AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
# Try npm ci, fallback to npm install
RUN npm ci || npm install

COPY frontend/ .
RUN npm run build

# ==========================================
# 2. BACKEND BUILD STAGE
# ==========================================
FROM python:3.11 AS backend-build

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1


# Create user early
RUN useradd -m myuser

WORKDIR /app/backend

# Install backend dependencies (system packages)
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
    rm -rf /var/lib/apt/lists/*

# Disable GUI display (headless)
ENV QT_QPA_PLATFORM=offscreen

# Install MuseScore 4
ENV MSCORE_VERSION=4.5.2.251141401
ENV MSCORE_APPIMAGE=MuseScore-Studio-${MSCORE_VERSION}-x86_64.AppImage

RUN wget -O /tmp/mscore.AppImage https://cdn.jsdelivr.net/musescore/v4.5.2/${MSCORE_APPIMAGE} && \
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

RUN chown -R myuser:myuser /app/backend

# ==========================================
# 3. FINAL STAGE
# ==========================================
FROM python:3.11-slim AS production

# Disable GUI display (headless)
ENV QT_QPA_PLATFORM=offscreen

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gettext \
    nginx \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
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
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend
COPY --from=backend-build /app/backend /app/backend

# Copy MuseScore from backend-build
COPY --from=backend-build /opt/musescore /opt/musescore
RUN ln -s /opt/musescore/AppRun /usr/local/bin/mscore4

# Copy frontend build to Nginx
COPY --from=frontend-build /app/frontend/dist /var/www/html

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy Nginx config
COPY ./nginx.conf /etc/nginx/nginx.conf

# Start script
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

WORKDIR /app/backend


EXPOSE 80

CMD ["/start.sh"]
