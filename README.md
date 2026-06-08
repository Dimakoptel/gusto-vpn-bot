# GUSTO VPN Bot v2.0 — Исправленная версия

> ⚡ Быстрый. Безопасный. Без границ. | Управление через админ-панель

## 🚀 Быстрый старт

### 1. Подготовка
```bash
cd /workspaces/gusto-vpn-bot
```

Если Docker и Docker Compose ещё не установлены:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

### 2. Скопировать пример окружения
```bash
cp .env.example .env
nano .env
```

Обязательные параметры:
- `DB_PASSWORD` — пароль для PostgreSQL
- `SECRET_KEY` — секретный ключ для backend
- `CORS_ORIGINS` — origin для доступа из браузера
- `BOT_TOKEN` — можно оставить пустым, если токен будет задать через backend
- `REACT_APP_API_URL` — URL backend для админ-панели

### 3. Запуск контейнеров
```bash
docker compose up -d --build
```

Если у вас старая версия Docker Compose:
```bash
docker-compose up -d --build
```

### 4. Прогон миграций
```bash
docker compose exec backend alembic upgrade head
```

### 5. Инициализация тарифов
```bash
curl -X POST http://localhost:8000/api/plans/seed
```

### 6. Админ-панель
- Админ-панель доступна через nginx на `http://localhost` или `https://<ваш-сервер>`
- Backend API выходит на `http://localhost:8000`
- Если бот не знает токен, он автоматически будет запрашивать его у backend по адресу `/settings/bot`

## 🖥️ Развертывание на локальном хосте

1. Скопируйте репозиторий и создайте `.env`.
2. Запустите все сервисы:
```bash
docker compose up -d --build
```
3. Проверьте сервисы:
```bash
docker compose ps
curl http://localhost:8000/health/
```
4. Откройте админ-панель и задайте токен бота, если он не добавлен автоматически.

## 🌐 Развертывание на VPS

1. Установите Docker и Docker Compose:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```
2. Склонируйте репозиторий:
```bash
git clone https://github.com/Dimakoptel/gusto-vpn-bot.git
cd gusto-vpn-bot
```
3. Создайте `.env` из `.env.example` и настройте переменные.
4. Скопируйте SSL-сертификаты в `docker/nginx/ssl`, если хотите HTTPS.
5. Запустите контейнеры:
```bash
docker compose up -d --build
```
6. Выполните миграции:
```bash
docker compose exec backend alembic upgrade head
```
7. Проверьте:
```bash
docker compose logs backend --tail=30
curl http://localhost:8000/health/
```

## 🔧 Проверка работы

- `docker compose ps`
- `curl http://localhost:8000/health/`
- `curl http://localhost:8000/settings/bot`
- `docker compose logs bot --tail=30`
- Откройте админ-панель по `http://localhost` или вашему домену

## 🎯 Что важно

- Бот может загружать токен динамически из backend, если `BOT_TOKEN` пустой.
- Для запуска backend и админки на одном хосте используется `nginx`.
- `postgres` и `redis` запускаются как сервисы Docker.

## 🔧 Исправленные проблемы (v2.0-fixed)

| # | Проблема | Исправление |
|---|----------|-------------|
| 1 | Неверные импорты `backend.app` | Заменены на `app` |
| 2 | ConfigService синхронный | Переписан на async |
| 3 | Нет plans_router | Добавлен в `backend/app/routers/__init__.py` |
| 4 | Нет модели SystemSettings | Создана полная модель (см. backend/app/models/settings.py) |
| 5 | Нет `backend/app/dependencies.py` | Создан JWT auth |
| 6 | ConfigService.get_many() не существует | Добавлен async метод |
| 7 | NotificationService неправильно использует ConfigService | Исправлено на async |
| 8 | Бот не загружает admin_ids из API | Добавлена загрузка из `/api/settings/health` |
| 9 | Webhook IP whitelist закомментирован | Включен |
| 10 | CORS `allow_origins=["*"]` | Ограничен через `.env` |
| 11 | `backend/app/routers/subscriptions.py` — неверные импорты | Исправлены |
| 12 | Нет `import os` в `bot/main.py` | Добавлен |
| 13 | `backend/app/models/server.py` — нет `consecutive_fails` | Добавлены поля |
| 14 | Backup command | Исправлен |
| 15 | admin-panel exposed на 3000 | Убраны ports |
| 16 | `backend/alembic.ini` | Файл находится в `backend/alembic.ini` (если нужен на уровне проекта — добавьте вручную) |

## 📁 Структура проекта
```
gusto-vpn-bot/
├── backend/
│   ├── app/
│   │   ├── models/          # Все модели (User, Server, Plan, Subscription, Payment, Settings)
│   │   ├── routers/         # API endpoints (users, servers, plans, payments, subscriptions, referrals, admin, settings, health)
│   │   ├── services/        # Business logic (config, subscription, notification, x3ui client)
│   │   ├── tasks/           # Background tasks (APScheduler)
│   │   ├── backend/app/main.py          # FastAPI app + lifespan
│   │   ├── backend/app/database.py      # Async SQLAlchemy + Redis
│   │   ├── backend/app/config.py        # CoreSettings + DynamicSettingsProxy
│   │   └── backend/app/dependencies.py  # JWT auth
│   ├── requirements.txt
│   └── Dockerfile
├── bot/
│   ├── bot/main.py              # aiogram bot + ConfigService + error handling
│   ├── requirements.txt
│   └── Dockerfile
├── admin-panel/
│   └── src/
│       ├── admin-panel/src/services/api.js
│       └── views/           # 6 React компонентов настроек (см. admin-panel/src/views/)
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
