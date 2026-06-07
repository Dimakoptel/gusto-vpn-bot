#!/bin/bash
set -e

echo "🚀 GUSTO VPN Backend starting..."

echo "⏳ Waiting for PostgreSQL..."
while ! nc -z gusto-postgres 5432; do
  sleep 1
done
echo "✅ PostgreSQL is ready"

echo "⏳ Waiting for Redis..."
while ! nc -z gusto-redis 6379; do
  sleep 1
done
echo "✅ Redis is ready"

echo "🔄 Running database migrations..."
alembic upgrade head

echo "🎯 Starting GUSTO API..."
exec "$@"
