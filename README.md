# GUSTO VPN Bot v2.0 — Production Ready

## 🚀 Что нового в v2.0

### Полная интеграция админ-панели
- **Все настройки** через веб-интерфейс (больше не нужно редактировать `.env`!)
- **6 табов**: Бот, Платежи, Рефералка, Антифрод, Уведомления, Система
- **Тест подключения** платежных систем прямо в UI
- **Live-превью** расчета реферальных комиссий

### Рабочий flow покупки
- **Активация подписки** после оплаты (автоматически через webhook)
- **Smart Router** выбирает лучший сервер
- **QR-коды** с подписью для каждой подписки
- **Продление** через bulkAdjust API

### Production-ready инфраструктура
- **Graceful shutdown** бота (сохранение состояний)
- **Circuit breaker** для backend API
- **Rate limiting** на рассылки (1 msg/sec)
- **IP whitelist** для webhook'ов платежных систем
- **Health checks** для всех сервисов Docker
- **Автоматический бэкап** PostgreSQL (ежедневно в 3:00)

### 5 дефолтных тарифов
- GUSTO Start (199₽, 50GB)
- GUSTO Pro (349₽, 100GB) — популярный
- GUSTO Ultra (599₽, 200GB) — premium
- GUSTO 3 месяца (899₽, 300GB) — экономия 15%
- GUSTO 1 год (2999₽, 1200GB) — экономия 30%

---

## 📁 Структура файлов (v2.0)

```
gusto-vpn-bot/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── __init__.py          # + GustoPlan, AppConfig
│   │   │   ├── server.py            # + panel_api_token
│   │   │   ├── user.py              # (без изменений)
│   │   │   ├── subscription.py      # (без изменений)
│   │   │   ├── payment.py           # (без изменений)
│   │   │   └── plan.py              # ✅ НОВЫЙ
│   │   ├── routers/
│   │   │   ├── settings.py          # ✅ Обновлен (admin endpoints)
│   │   │   ├── payments.py          # ✅ Обновлен (активация, webhooks)
│   │   │   ├── plans.py             # ✅ НОВЫЙ (CRUD + seed)
│   │   │   └── ...
│   │   ├── services/
│   │   │   ├── config_service.py    # ✅ Обновлен (Redis cache)
│   │   │   ├── subscription_service.py  # ✅ НОВЫЙ (активация, продление)
│   │   │   ├── notification_service.py  # ✅ НОВЫЙ (15+ типов уведомлений)
│   │   │   └── x3ui_client.py       # ✅ Обновлен (v3.x API)
│   │   ├── tasks/
│   │   │   └── background_tasks.py  # ✅ НОВЫЙ (6 фоновых задач)
│   │   └── main.py                  # ✅ Обновлен (lifespan, routers)
│   ├── requirements.txt             # + apscheduler
│   └── Dockerfile
├── bot/
│   └── main.py                      # ✅ Обновлен (ConfigService, error handling, graceful shutdown)
├── admin-panel/
│   └── src/
│       ├── views/                   # ✅ 6 React компонентов настроек
│       └── services/api.js          # ✅ Axios + Bearer auth
├── docker/
│   ├── docker-compose.yml           # ✅ Production-ready (6 сервисов)
│   └── nginx/nginx.conf             # ✅ SSL + rate limiting
├── alembic/
│   └── versions/
│       ├── 001_replace_panel_creds_with_token.py  # ✅ Миграция
│       └── 002_add_plans_and_fixes.py             # ✅ Миграция
├── tests/
│   └── test_suite.py                # ✅ 8+ тестов
└── .env.example                     # ✅ Минимальные переменные
```

---

## 🛠️ Установка и запуск

### 1. Клонировать и настроить

```bash
git clone https://github.com/Dimakoptel/gusto-vpn-bot.git
cd gusto-vpn-bot
cp .env.example .env
# Отредактируйте .env — минимум: BOT_TOKEN, DB_PASSWORD, SECRET_KEY
```

### 2. Запуск через Docker

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker/docker-compose.yml up -d
```

### 3. Миграции базы данных

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Инициализация

```bash
# Создать дефолтные тарифы
curl -X POST http://localhost:8000/api/plans/seed

# Настройки через админ-панель
# Откройте http://localhost:3000/settings
```

### 5. Настройка через админ-панель

1. Откройте `http://your-domain.com/admin`
2. Перейдите в **Settings**
3. **Bot**: введите токен от @BotFather, ID админов
4. **Payments**: включите провайдеров, введите токены, нажмите **Проверить**
5. **Referral**: настройте % комиссии
6. **System**: включите/выключите maintenance mode

---

## 📋 API Endpoints

### Settings
```
GET    /api/settings/                    # Все настройки
PUT    /api/settings/                    # Обновить
PATCH  /api/settings/bot                 # Только бот
PATCH  /api/settings/payments            # Только платежи
PATCH  /api/settings/referral          # Только рефералка
PATCH  /api/settings/antifraud         # Только антифрод
PATCH  /api/settings/notifications     # Только уведомления
PATCH  /api/settings/system            # Только система
GET    /api/settings/payments/{provider}/test  # Тест провайдера
GET    /api/settings/health              # Публичный статус
```

### Plans
```
GET    /api/plans/                       # Список тарифов
GET    /api/plans/{id}                   # Тариф по ID
POST   /api/plans/                       # Создать тариф
PUT    /api/plans/{id}                   # Обновить тариф
DELETE /api/plans/{id}                   # Удалить (soft)
POST   /api/plans/seed                   # Создать дефолтные тарифы
```

### Payments
```
POST   /api/payments/                    # Создать платеж
GET    /api/payments/{id}               # Статус платежа
POST   /api/payments/webhook/cryptobot   # Webhook CryptoBot
POST   /api/payments/webhook/yookassa    # Webhook YooKassa
POST   /api/payments/webhook/freekassa   # Webhook FreeKassa
POST   /api/payments/{id}/refund         # Возврат (YooKassa)
```

---

## 🔧 Переменные окружения (.env)

| Переменная | Обязательная | Описание |
|------------|-------------|----------|
| `BOT_TOKEN` | ✅ | Токен от @BotFather |
| `DB_PASSWORD` | ✅ | Пароль PostgreSQL |
| `SECRET_KEY` | ✅ | Секретный ключ для JWT |
| `BACKEND_URL` | ❌ | URL backend (default: http://backend:8000) |
| `REDIS_URL` | ❌ | URL Redis (default: redis://redis:6379/0) |

**Все остальные настройки** управляются через админ-панель и хранятся в БД!

---

## 🔄 Жизненный цикл подписки

```
[Пользователь] → Выбор тарифа → Создание PENDING подписки
     ↓
[Оплата] → Webhook от провайдера → Активация подписки
     ↓
[3x-ui] → Создание клиента → Генерация конфига → QR-код
     ↓
[Telegram] → Отправка конфига пользователю
     ↓
[Background] → Мониторинг трафика → Уведомления → Продление/Истечение
```

---

## 🛡️ Безопасность

- ✅ Bearer Token для 3x-ui API (не cookie)
- ✅ IP whitelist для webhook'ов платежей
- ✅ Sensitive-флаг для токенов в админ-панели
- ✅ Rate limiting: 1 msg/sec на рассылки
- ✅ Circuit breaker для backend API
- ✅ Graceful shutdown (сохранение состояний)
- ✅ Автоматический бэкап БД

---

## 📊 Мониторинг

### Health Checks
- `GET /health` — общий статус
- `GET /api/settings/health` — статус системы (публичный)

### Логи
```bash
# Backend
docker-compose logs -f backend

# Bot
docker-compose logs -f bot

# Все сервисы
docker-compose logs -f
```

### Prometheus (опционально)
Добавьте `/metrics` endpoint для сбора метрик.

---

## 🧪 Тесты

```bash
cd backend
pytest tests/test_suite.py -v
```

---

## 📝 Лицензия

MIT License — свободное использование и модификация.

---

**GUSTO VPN — Быстрый. Безопасный. Без границ.** 🚀
