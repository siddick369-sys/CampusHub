#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore_db.sh path/to/backup.sql.gz"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file not found"
    exit 1
fi

if [ ! -f .env ]; then
    echo ".env file not found"
    exit 1
fi

export $(grep -v '^#' .env | xargs)

CONTAINER_ID=$(docker-compose ps -q postgres)

if [ -z "$CONTAINER_ID" ]; then
  echo "Postgres container not running"
  exit 1
fi

echo "Restoring database from $BACKUP_FILE..."

gunzip -c $BACKUP_FILE | docker exec -i $CONTAINER_ID psql -U $DB_USER $DB_NAME

echo "Restore completed successfully."