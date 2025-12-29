FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV QT_QPA_PLATFORM=offscreen

# --------------------------------------------------
# MuseScore runtime deps
# --------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    wget \
    xvfb \
    xauth \
    x11-xserver-utils \
    libfuse2 \
    libxkbcommon-x11-0 \
    libxcb1 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-render-util0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libopengl0 \
    libgl1 \
    libglx0 \
    libegl1 \
    libglu1-mesa \
    libasound2 \
    libjack-jackd2-0 \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto \
    fonts-freefont-ttf \
    libglib2.0-0 \
    libnss3 \
    libgpg-error0 \
    python3 \
    python3-pip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Install MuseScore
# --------------------------------------------------
WORKDIR /opt

RUN wget -O MuseScore.AppImage \
      https://github.com/musescore/MuseScore/releases/download/v4.6.2/MuseScore-Studio-4.6.2.252830930-x86_64.AppImage && \
    chmod +x MuseScore.AppImage && \
    ./MuseScore.AppImage --appimage-extract && \
    mv squashfs-root musescore && \
    rm MuseScore.AppImage

# --------------------------------------------------
# Install Fonts
# --------------------------------------------------
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# --------------------------------------------------
# Headless wrapper
# --------------------------------------------------
RUN echo '#!/bin/bash\nexec xvfb-run -a /opt/musescore/AppRun "$@"' \
    > /usr/local/bin/musescore && \
    chmod +x /usr/local/bin/musescore

# --------------------------------------------------
# FastAPI
# --------------------------------------------------
RUN pip3 install --no-cache-dir --break-system-packages fastapi uvicorn python-multipart

WORKDIR /app
COPY musescore-headless/app.py .

# --------------------------------------------------
# Non-root user
# --------------------------------------------------
RUN useradd -m -u 1000 musescore
USER musescore

RUN fc-cache -f -v

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "1234"]
