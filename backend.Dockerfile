FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

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
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------
# Python dependencies
# --------------------------------------------------
COPY backend/requirements.txt .
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
# Application code
# --------------------------------------------------
COPY backend .

EXPOSE 8000

# --------------------------------------------------
# Non-root user
# --------------------------------------------------
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
