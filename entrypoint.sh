#!/bin/bash

# exit immediately if a command exits with a non-zero status
set -e

# --- WAIT FOR POSTGRES ---
echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.5
done
echo "PostgreSQL started"

# --- WAIT FOR REDIS ---
echo "Waiting for Redis..."
while ! nc -z $REDIS_HOST $REDIS_PORT; do
  sleep 0.5
done
echo "Redis started"

# --- CHECK CRITICAL ENV VARS ---
if [ -z "$SECRET_KEY" ]; then
    echo "ERROR: SECRET_KEY is not set"
    exit 1
fi

# --- DJANGO SETUP ---
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# --- START COMMAND ---
echo "Starting application with command: $@"
exec "$@"
