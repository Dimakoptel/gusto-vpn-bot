
# GUSTO VPN Bot — Обновление: Все 3 этапа

## Сводка изменений

### Этап 1: Обновленный x3ui_client.py
**Файл:** `backend/app/services/x3ui_client.py`

**Ключевые изменения:**
- ❌ Убрана cookie-based авторизация (POST /login)
- ✅ Добавлена Bearer Token авторизация (`Authorization: Bearer <token>`)
- ❌ Убраны устаревшие endpoints: `/xui/API/inbounds/...`, `/updateClient`, `/updateClients`
- ✅ Добавлены актуальные endpoints из MHSanaei/3x-ui v3.x:
  - `GET /panel/api/inbounds/list`
  - `GET /panel/api/inbounds/get/{id}`
  - `POST /panel/api/clients/add`
  - `POST /panel/api/clients/update/{email}`
  - `POST /panel/api/clients/del/{email}`
  - `GET /panel/api/clients/traffic/{email}`
  - `GET /panel/api/clients/links/{email}`
  - `POST /panel/api/clients/bulkAdjust`
  - `POST /panel/api/clients/bulkDel`
  - `POST /panel/api/clients/resetTraffic/{email}`
  - `GET /panel/api/server/status`
  - `POST /panel/api/server/restartXrayService`

**Новые методы:**
- `create_client()` — создание клиента через `/clients/add`
- `update_client()` — обновление через `/clients/update/{email}`
- `delete_client()` — удаление через `/clients/del/{email}`
- `bulk_adjust_clients()` — продление/добавление трафика
- `bulk_delete_clients()` — массовое удаление
- `get_client_links()` — получение ссылок подключения
- `get_online_clients()` — мониторинг онлайн клиентов
- `generate_vless_link()` — генерация VLESS Reality ссылок
- `generate_vmess_link()` — генерация VMess ссылок
- `generate_trojan_link()` — генерация Trojan ссылок

**Важно:** Теперь в модели `GustoServer` нужно хранить `panel_api_token` вместо `panel_username` + `panel_password`!

---

### Этап 2: Полноценный Telegram Bot
**Файл:** `bot/main.py`

**Что было:**
- Полностью статические заглушки (mock)
- Захардкоженные ID, цены, данные
- Нет интеграции с backend

**Что стало:**
- ✅ Полная интеграция с backend API через HTTP клиент
- ✅ FSM (Finite State Machine) для flow покупки
- ✅ Реальные данные из PostgreSQL
- ✅ Полный flow покупки: выбор тарифа -> выбор способа оплаты -> оплата -> получение конфигурации
- ✅ Проверка статуса платежа
- ✅ Личный кабинет с реальными подписками
- ✅ Детали подписки (трафик, срок, сервер)
- ✅ Копирование конфигурации
- ✅ Реферальная система (ссылка, статистика)
- ✅ Поддержка (сообщения в support)
- ✅ Админ-меню (для is_admin=True)

**FSM States:**
- `BuyFlow.select_plan` — выбор тарифа
- `BuyFlow.select_payment` — выбор способа оплаты
- `BuyFlow.waiting_payment` — ожидание оплаты
- `SupportFlow.write_message` — написание в поддержку

**BackendClient методы:**
- `get_user()` — получить/создать пользователя
- `get_plans()` — список тарифов
- `create_subscription()` — создать подписку
- `get_user_subscriptions()` — подписки пользователя
- `get_subscription()` — детали подписки
- `create_payment()` — создать платеж
- `get_payment_status()` — проверить статус
- `get_referral_stats()` — статистика рефералов

---

### Этап 3: Платежные системы
**Файл:** `backend/app/services/payments.py` + обновленный `backend/app/routers/payments.py`

**Реализовано:**

#### CryptoBot
- `create_payment()` — создание инвойса через API
- `check_payment()` — проверка статуса инвойса
- `verify_webhook()` — проверка подписи webhook
- `get_balance()` — баланс кошелька
- Поддержка USDT, TON, BTC

#### YooKassa (ЮKassa)
- `create_payment()` — создание платежа с receipt (чек 54-ФЗ)
- `check_payment()` — проверка статуса
- `verify_webhook()` — проверка webhook
- `refund_payment()` — возврат средств
- Поддержка idempotence key
- Фискальный чек (receipt) для РФ

#### FreeKassa
- `create_payment()` — генерация URL для оплаты
- `check_payment()` — проверка через API
- `verify_webhook()` — проверка MD5 подписи
- `get_payment_methods()` — список доступных способов

#### PaymentManager
- Единая точка входа для всех провайдеров
- `register_provider()` — регистрация
- `create_payment()` — создание через любой провайдер
- `check_payment()` — проверка статуса
- `verify_webhook()` — верификация webhook

**Backend Routers (FastAPI):**
- `POST /api/payments/` — создание платежа
- `GET /api/payments/{payment_id}` — проверка статуса
- `POST /api/payments/webhook/cryptobot` — webhook CryptoBot
- `POST /api/payments/webhook/yookassa` — webhook YooKassa
- `POST /api/payments/webhook/freekassa` — webhook FreeKassa

---

## Что нужно сделать для запуска

### 1. Обновить модель GustoServer
Добавить поле `panel_api_token` (убрать username/password):
```python
# backend/app/models/server.py
# Убрать:
# panel_username = Column(String(255))
# panel_password = Column(Text)

# Добавить:
panel_api_token = Column(Text)  # API Token из 3x-ui Settings -> API Token
```

### 2. Обновить .env
```
GUSTO_CRYPTOBOT_TOKEN=your_cryptobot_token
GUSTO_YOOKASSA_SHOP_ID=your_shop_id
GUSTO_YOOKASSA_SECRET_KEY=your_secret_key
GUSTO_FREEKASSA_ID=your_shop_id
GUSTO_FREEKASSA_SECRET=your_secret
GUSTO_FREEKASSA_API_KEY=your_api_key
```

### 3. Получить API Token из 3x-ui
1. Открыть панель 3x-ui
2. Settings -> API Token
3. Скопировать токен
4. Вставить в `panel_api_token` для каждого сервера

### 4. Запустить миграции
```bash
cd backend
alembic revision --autogenerate -m "add panel_api_token"
alembic upgrade head
```

### 5. Запустить
```bash
make dev  # или docker-compose up --build
```

---

## Файлы для замены

| Оригинальный файл | Новый файл | Статус |
|-------------------|------------|--------|
| backend/app/services/x3ui_client.py | updated_x3ui_client.py | ✅ Готов |
| bot/main.py | updated_bot.py | ✅ Готов |
| backend/app/routers/payments.py | updated_payments.py | ✅ Готов |
| backend/app/routers/subscriptions.py | updated_subscriptions_router.py | ✅ Готов |

---

## Что осталось доработать (P1-P2)

### P1 (Важно):
- [ ] Фоновые задачи (APScheduler): проверка истекающих, авто-удаление
- [ ] Уведомления в Telegram (expiry 3/1 день, low traffic)
- [ ] Полная интеграция webhook -> активация подписки
- [ ] Генерация QR кодов для конфигураций
- [ ] Обработка ошибок и retry логика

### P2 (Желательно):
- [ ] Мониторинг изменений 3x-ui через GitHub API
- [ ] Тесты (pytest)
- [ ] Production Docker Compose
- [ ] Бэкапы базы данных
- [ ] Мониторинг (Prometheus + Grafana)
- [ ] Rate limiting

---

*Подготовлено: 2026-06-07*
*Автор: AI Assistant*
