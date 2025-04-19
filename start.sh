#!/bin/sh

# 🚨 Manually ensure DATABASE_URL is exported
export DATABASE_URL="${DATABASE_URL:-$DATABASE_PUBLIC_URL}"

echo "ENV VARS:"
env
echo "------------"
echo "DATABASE_URL: $DATABASE_URL"

# Fail fast if DATABASE_URL is missing
if [ -z "$DATABASE_URL" ]; then
  echo "❌ DATABASE_URL is not set"
  exit 1
fi

# Apply migrations
alembic upgrade head

# Start the app
uvicorn main:app --host 0.0.0.0 --port 8000
