#!/bin/sh

# Fail fast if DATABASE_URL is missing
if [ -z "$DATABASE_URL" ]; then
  echo "❌ DATABASE_URL is not set"
  exit 1
fi

# Apply migrations
alembic upgrade head

# Start the app
uvicorn main:app --host 0.0.0.0 --port 8000
