#!/bin/bash
set -e

# --- Load env vars safely ---
if [ ! -f .env ]; then
  echo ".env file not found"
  exit 1
fi

export $(grep -v '^#' .env | xargs)

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="campushub_db_backup_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR

echo "Starting backup of database: $DB_NAME"

# Get container ID dynamically
CONTAINER_ID=$(docker-compose ps -q postgres)

if [ -z "$CONTAINER_ID" ]; then
  echo "Postgres container not running"
  exit 1
fi

docker exec $CONTAINER_ID pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/$FILENAME

gzip $BACKUP_DIR/$FILENAME

echo "Backup completed: $BACKUP_DIR/$FILENAME.gz"

# Keep only last 10 backups
ls -tp $BACKUP_DIR/*.gz | grep -v '/$' | tail -n +11 | xargs -I {} rm -- {}