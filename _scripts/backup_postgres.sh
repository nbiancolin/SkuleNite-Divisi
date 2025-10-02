#!/bin/bash
set -e

export $(grep -v '^#' .env | xargs)

DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="$BACKUP_DIR/${DB_NAME}_$DATE.sql.gz"

#Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

PGPASSWORD="$DB_PASS" pg_dump \
  -h $DB_HOST \
  -p $DB_PORT \
  -U $DB_USER \
  $DB_NAME | gzip > "$FILENAME"

#Keep only last 7 backups
ls -t $BACKUP_DIR/*.gz | tail -n +8 | xargs rm -f || true