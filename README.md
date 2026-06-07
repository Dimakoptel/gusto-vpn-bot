# GUSTO VPN Bot v2.0 — Исправленная версия

> ⚡ Быстрый. Безопасный. Без границ. | Управление через админ-панель

## 🚀 Быстрый старт

### 1. Настройка окружения
```bash
cp .env.example .env
nano .env  # Отредактируйте BOT_TOKEN, DB_PASSWORD, SECRET_KEY
```

### 2. Запуск
```bash
docker-compose up -d
```

### 3. Миграции и seed
```bash
docker-compose exec backend alembic upgrade head
curl -X POST http://localhost:8000/api/plans/seed
```

### 4. Админ-панель
Откройте http://localhost:3000 и настройте:
- 🤖 Токен бота
- 💰 Платежные провайдеры
- 🤝 Реферальные %
- 🛡️ Антифрод
- 🔔 Уведомления

## 🔧 Исправленные проблемы (v2.0-fixed)

| # | Проблема | Исправление |
|---|----------|-------------|
| 1 | Неверные импорты `backend.app` | Заменены на `app` |
| 2 | ConfigService синхронный | Переписан на async |
| 3 | Нет plans_router | Добавлен в `__init__.py` |
| 4 | Нет модели SystemSettings | Создана полная модель |
| 5 | Нет dependencies.py | Создан JWT auth |
| 6 | ConfigService.get_many() не существует | Добавлен async метод |
| 7 | NotificationService неправильно использует ConfigService | Исправлено на async |
| 8 | Бот не загружает admin_ids из API | Добавлена загрузка из `/api/settings/health` |
| 9 | Webhook IP whitelist закомментирован | Включен |
| 10 | CORS `allow_origins=["*"]` | Ограничен через `.env` |
| 11 | subscriptions.py — неверные импорты | Исправлены |
| 12 | Нет `import os` в bot/main.py | Добавлен |
| 13 | server.py — нет `consecutive_fails` | Добавлены поля |
| 14 | Backup command | Исправлен |
| 15 | admin-panel exposed на 3000 | Убраны ports |
| 16 | Нет alembic.ini | Нужно добавить вручную |

## 📁 Структура проекта
```
gusto-vpn-bot/
├── backend/
│   ├── app/
│   │   ├── models/          # Все модели (User, Server, Plan, Subscription, Payment, Settings)
│   │   ├── routers/         # API endpoints (users, servers, plans, payments, subscriptions, referrals, admin, settings, health)
│   │   ├── services/        # Business logic (config, subscription, notification, x3ui client)
│   │   ├── tasks/           # Background tasks (APScheduler)
│   │   ├── main.py          # FastAPI app + lifespan
│   │   ├── database.py      # Async SQLAlchemy + Redis
│   │   ├── config.py        # CoreSettings + DynamicSettingsProxy
│   │   └── dependencies.py  # JWT auth
│   ├── requirements.txt
│   └── Dockerfile
├── bot/
│   ├── main.py              # aiogram bot + ConfigService + error handling
│   ├── requirements.txt
│   └── Dockerfile
├── admin-panel/
│   └── src/
│       ├── services/api.js
│       └── views/           # 6 React компонентов настроек
├── docker-compose.yml       # 6 сервисов
├── .env.example
└── tests/test_suite.py
```

## 📋 API Endpoints

```
GET    /health/                          # Health check
GET    /api/settings/                     # Все настройки (admin)
PUT    /api/settings/                     # Обновить настройки
PATCH  /api/settings/bot                 # Только бот
PATCH  /api/settings/payments            # Только платежи
PATCH  /api/settings/referral            # Только рефералка
PATCH  /api/settings/antifraud           # Только антифрод
PATCH  /api/settings/notifications       # Только уведомления
PATCH  /api/settings/system              # Только система
POST   /api/settings/payments/{provider}/test  # Тест провайдера
GET    /api/settings/health               # Публичный статус
GET    /api/plans/                        # Список тарифов
POST   /api/plans/seed                    # Seed default plans
GET    /api/users/telegram/{id}          # Пользователь по Telegram ID
POST   /api/payments/                     # Создать платеж
POST   /api/payments/webhook/cryptobot    # Webhook CryptoBot
POST   /api/payments/webhook/yookassa     # Webhook YooKassa
POST   /api/payments/webhook/freekassa    # Webhook FreeKassa
POST   /api/subscriptions/pending          # Создать pending подписку
POST   /api/subscriptions/{id}/activate  # Активировать подписку
```

## 🎯 Проверка перед деплоем

- [ ] `docker-compose up -d` запускает все сервисы
- [ ] `curl http://localhost:8000/health/` возвращает 200
- [ ] `curl http://localhost:8000/api/settings/health` возвращает JSON
- [ ] Админ-панель открывается
- [ ] Seed тарифов работает
- [ ] Бот отвечает на /start
- [ ] Webhook endpoints доступны извне

## 📝 Лицензия
MIT
