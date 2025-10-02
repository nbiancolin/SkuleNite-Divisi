export $(grep -v '^#' .env | xargs)

if [ -z "$1" ]; then
  echo "Usage: $0 <backup_file.sql.gz>"
  exit 1
fi

gunzip -c "$1" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h $POSTGRES_HOST \
  -p $POSTGRES_PORT \
  -U $POSTGRES_USER \
  -d $POSTGRES_DB