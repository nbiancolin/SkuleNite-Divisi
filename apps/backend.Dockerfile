FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------
# System dependencies
# --------------------------------------------------
RUN apt-get update && apt-get install -y \
    # Build essentials for Python packages
    gcc \
    g++ \
    make \
    # Database clients / headers
    postgresql-client \
    default-libmysqlclient-dev \
    # Utilities
    curl \
    git \
    fontconfig \
    unzip \
    ca-certificates \
    # WeasyPrint dependencies
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# App structure (IMPORTANT for relative imports)
# --------------------------------------------------
WORKDIR /app

# Copy backend + packages so ../../packages works
COPY apps/backend /app/apps/backend
COPY packages /app/packages

# Move into backend directory
WORKDIR /app/apps/backend

# --------------------------------------------------
# Python dependencies
# --------------------------------------------------
RUN pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------
# Install Fonts
# --------------------------------------------------
COPY assets/fonts.zip /tmp/fonts.zip
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    unzip /tmp/fonts.zip -d /usr/share/fonts/truetype/custom && \
    fc-cache -fv && \
    rm -f /tmp/fonts.zip

# --------------------------------------------------
# Non-root user
# --------------------------------------------------
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# --------------------------------------------------
# Runtime
# --------------------------------------------------
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]