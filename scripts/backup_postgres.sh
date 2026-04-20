#!/bin/bash
set -e

# Resolve path to the .env file relative to this script
SCRIPT_DIR=$(dirname "$(realpath "$0")")
ENV_FILE="$SCRIPT_DIR/../backend/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

# Load variables from .env
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Timestamp
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/postgres"
FILENAME="${BACKUP_DIR}/${POSTGRES_DB}_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Run pg_dump inside the Postgres container
docker exec -i app-db-1 \
  sh -c "PGPASSWORD=$POSTGRES_PASSWORD pg_dump -U $POSTGRES_USER $POSTGRES_DB" \
  | gzip > "$FILENAME"

# Keep only last 7 backups
ls -t $BACKUP_DIR/*.gz | tail -n +8 | xargs rm -f || true
