FROM debian:bookworm-slim

ARG DEV=false

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
    python3-pytest \
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
COPY apps/musescore-headless/app.py .

#TOOD only if dev
COPY apps/musescore-headless/test_plugins.py .
COPY apps/musescore-headless/plugin_runner.py .
COPY apps/musescore-headless/fixtures ./fixtures

# --------------------------------------------------
# Non-root user and plugins
# --------------------------------------------------
RUN useradd -m -u 1000 musescore

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# MuseScore must run once to create its user config and Documents/MuseScore4/Plugins
RUN runuser -u musescore -- timeout 60 musescore -F >/dev/null 2>&1 || true

COPY apps/musescore-headless/plugins /home/musescore/Documents/MuseScore4/Plugins

RUN python3 -c "\
import glob, json, os; \
plugins_dir = '/home/musescore/Documents/MuseScore4/Plugins'; \
config_dir = '/home/musescore/.local/share/MuseScore/MuseScore4/plugins'; \
os.makedirs(config_dir, exist_ok=True); \
plugins = [{'codeKey': os.path.splitext(os.path.basename(path))[0], 'enabled': True} for path in glob.glob(plugins_dir + '/*.qml')]; \
json.dump(plugins, open(config_dir + '/plugins.json', 'w')) \
" && chown -R musescore:musescore /home/musescore

USER musescore

RUN fc-cache -f -v

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "1234"]
