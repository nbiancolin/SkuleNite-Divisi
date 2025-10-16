
#TODO: Pin this to a specific version!
FROM ubuntu

#install python
RUN apt-get update && apt-get install -y python3 python3-pip

# Create user early
RUN useradd -m myuser

WORKDIR /app

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

