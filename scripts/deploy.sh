#!/bin/bash
# GUSTO VPN Bot — Production Deployment
# Быстрый. Безопасный. Без границ.

set -e

echo "🚀 GUSTO VPN Bot Deployment"

if [ ! -f .env ]; then
    echo "❌ .env file not found! Copy from .env.example"
    exit 1
fi

git pull origin main 2>/dev/null || true

docker-compose -f docker/docker-compose.prod.yml pull
docker-compose -f docker/docker-compose.prod.yml up -d --build --remove-orphans

sleep 5
curl -sf http://localhost:8000/health || exit 1

docker system prune -f

echo ""
echo "✅ GUSTO VPN Bot deployed!"
echo "🌐 Admin: http://localhost:3000"
echo "🤖 Bot: @gustovpn_bot"
