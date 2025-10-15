FROM python:3.11

ENV DEBIAN_FRONTEND=noninteractive

# Create user early
RUN useradd -m myuser

WORKDIR /app

# Install dependencies
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
        libgpg-error0 \
        libxcb1 \
        p7zip-full && \
    rm -rf /var/lib/apt/lists/*

# Install Musescore Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb-cursor0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-render-util0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-util1 \
    libxkbcommon-x11-0 \
    libxrender1 \
    libx11-xcb1 \
    pipewire \
    xvfb \
 && rm -rf /var/lib/apt/lists/*


# Disable GUI display (headless)
ENV QT_QPA_PLATFORM=offscreen


# Install MuseScore 4 (extract AppImage)
ENV MSCORE_DOWNLOAD_LINK=https://cdn.jsdelivr.net/musescore/v4.6.2/MuseScore-Studio-4.6.2.252830930-x86_64.AppImage

RUN wget -O /tmp/mscore.AppImage "${MSCORE_DOWNLOAD_LINK}" && \
    chmod +x /tmp/mscore.AppImage && \
    cd /tmp && \
    ./mscore.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore && \
    ln -s /opt/musescore/AppRun /usr/local/bin/mscore4 && \
    rm /tmp/mscore.AppImage

# Copy and install custom fonts
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# Install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY backend/ .
RUN chown -R myuser:myuser /app

ENV PYTHONBUFFERED=1
USER myuser

RUN python _scripts/setup_music21.py

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]