FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

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

EXPOSE 8000

RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]