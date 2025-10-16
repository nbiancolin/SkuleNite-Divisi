FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip libfuse2 wget unzip fontconfig \
    libgl1 libx11-6 libnss3 libasound2 libjack0 libxcb-cursor0 libxcb-xinerama0 libxcb-keysyms1 \
 && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m myuser

WORKDIR /app
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONUNBUFFERED=1

# Install MuseScore 4
ENV MSCORE_DOWNLOAD_LINK=https://cdn.jsdelivr.net/musescore/v4.6.2/MuseScore-Studio-4.6.2.252830930-x86_64.AppImage
RUN wget -O /tmp/mscore.AppImage "${MSCORE_DOWNLOAD_LINK}" && \
    chmod +x /tmp/mscore.AppImage && \
    cd /tmp && \
    ./mscore.AppImage --appimage-extract && \
    mv squashfs-root /opt/musescore && \
    ln -s /opt/musescore/AppRun /usr/local/bin/mscore4 && \
    rm /tmp/mscore.AppImage

# Fonts
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# Python deps
COPY backend/requirements.txt .
RUN apt-get update && apt-get install -y git && \
    python3 -m pip install -r requirements.txt && \
    apt-get remove -y git && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*


# Copy app code
COPY backend/ .
RUN chown -R myuser:myuser /app
USER myuser

# Setup music21
RUN python3 _scripts/setup_music21.py

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
