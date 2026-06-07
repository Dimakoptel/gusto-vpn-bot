# 🚀 GUSTO VPN Bot

**Быстрый. Безопасный. Без границ.**

Telegram-бот для продажи VPN на базе 3x-ui с Smart Routing, реферальной системой и админ-панелью.

## Архитектура

```
gusto-vpn-bot/
├── backend/          # FastAPI + PostgreSQL + Redis
│   ├── app/
│   │   ├── models/   # SQLAlchemy models
│   │   ├── routers/  # API endpoints
│   │   ├── services/ # X3UI, Smart Router, Referral, AntiFraud
│   │   └── tasks/    # Background jobs
│   └── Dockerfile
├── bot/              # aiogram 3.x Telegram Bot
│   ├── handlers/     # Message handlers
│   ├── keyboards/    # Inline keyboards
│   └── services/   # API client, QR generator
├── admin-panel/      # React + Tailwind CSS
│   └── src/views/    # Dashboard, Users, Servers, Payments
└── docker/           # Docker Compose + Nginx
```

## Быстрый старт

```bash
# 1. Клонировать
 git clone <repo> && cd gusto-vpn-bot

# 2. Настроить окружение
cp .env.example .env
# Отредактировать .env

# 3. Запустить
make dev

# 4. Деплой
make prod
```

## API

- `GET /api/users` — список пользователей
- `POST /api/subscriptions` — создать подписку
- `GET /api/admin/dashboard` — статистика
- `GET /health` — health check

## Фичи

- ⚡ **Smart Router** — автовыбор лучшего сервера
- 🔒 **XTLS-Reality** — обход DPI
- 👥 **3-уровневая рефералка** (30%/15%/5%)
- 🛡️ **Anti-Fraud** — защита от абуза
- 💳 **CryptoBot + ЮKassa + FreeKassa**
- 📊 **Админ-панель** с real-time статистикой

## Лицензия

MIT © GUSTO VPN Team
