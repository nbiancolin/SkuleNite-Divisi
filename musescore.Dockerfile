FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV QT_QPA_PLATFORM=offscreen

# --------------------------------------------------
# Install runtime dependencies required by MuseScore
# --------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core system
    ca-certificates \
    bash \
    curl \
    wget \
    xz-utils \
    # X / headless rendering
    xvfb \
    xauth \
    x11-xserver-utils \
    # AppImage support
    libfuse2 \
    # Qt / XCB deps
    libxkbcommon-x11-0 \
    libxcb1 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxcb-render-util0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    # OpenGL / EGL
    libopengl0 \
    libgl1 \
    libglx0 \
    libegl1 \
    libglu1-mesa \
    # Audio (MuseScore expects these even headless)
    libasound2 \
    libjack-jackd2-0 \
    # Fonts
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto \
    fonts-freefont-ttf \
    # Misc
    libglib2.0-0 \
    libnss3 \
    libgpg-error0 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Install MuseScore 4 AppImage
# --------------------------------------------------
WORKDIR /opt

RUN wget -O MuseScore.AppImage \
      https://github.com/musescore/MuseScore/releases/download/v4.6.2/MuseScore-Studio-4.6.2.252830930-x86_64.AppImage && \
    chmod +x MuseScore.AppImage && \
    ./MuseScore.AppImage --appimage-extract && \
    mv squashfs-root musescore && \
    rm MuseScore.AppImage

# --------------------------------------------------
# Headless wrapper
# --------------------------------------------------
RUN echo '#!/bin/bash\nexec xvfb-run -a /opt/musescore/AppRun "$@"' \
    > /usr/local/bin/musescore && \
    chmod +x /usr/local/bin/musescore

# --------------------------------------------------
# Optional: non-root user (recommended)
# --------------------------------------------------
RUN useradd -m -u 1000 musescore
USER musescore
WORKDIR /home/musescore

# Prime font cache (avoids first-run hangs)
RUN fc-cache -f -v

# Default command
ENTRYPOINT ["musescore"]
CMD ["--help"]
