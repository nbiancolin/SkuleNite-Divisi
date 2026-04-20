export $(grep -v '^#' .env | xargs)

if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file.sql.gz>"
  exit 1
fi

gunzip -c "$1" \
  | docker exec -i app-db-1 \
    bash -c "PGPASSWORD=${POSTGRES_PASSWORD} psql \
      -U ${POSTGRES_USER} \
      -d ${POSTGRES_DB}"
