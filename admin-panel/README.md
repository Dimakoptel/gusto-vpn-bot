# GUSTO VPN Bot — Admin Panel Update

## Что добавлено

Полноценная веб-админ-панель для управления ВСЕМИ настройками проекта через интерфейс. Больше не нужно редактировать `.env` или перезапускать бота для смены токена/платежной системы.

---

## Структура файлов

### Backend

| Файл | Назначение |
|------|-----------|
| `backend/app/models/settings.py` | Модель `SystemSettings` — все настройки в БД |
| `backend/app/services/config_service.py` | Чтение/запись настроек с кэшем в Redis |
| `backend/app/routers/settings.py` | API endpoints для CRUD настроек |
| `backend/app/routers/payments_v2.py` | Платежи, читающие конфиг из SystemSettings |
| `alembic/versions/001_replace_panel_creds_with_token.py` | Миграция: +`panel_api_token`, +`system_settings` |

### Frontend (Admin Panel)

| Файл | Назначение |
|------|-----------|
| `admin-panel/src/views/SettingsPage.jsx` | Главная страница с табами |
| `admin-panel/src/views/BotSettings.jsx` | Токен бота, админы, welcome message |
| `admin-panel/src/views/PaymentSettings.jsx` | CryptoBot, YooKassa, FreeKassa + тест подключения |
| `admin-panel/src/views/ReferralSettings.jsx` | % рефералки, мин. вывод |
| `admin-panel/src/views/AntifraudSettings.jsx` | Лимиты IP/стран, бан |
| `admin-panel/src/views/NotificationSettings.jsx` | Уведомления об истечении |
| `admin-panel/src/views/SystemSettings.jsx` | Название, логотип, maintenance mode |
| `admin-panel/src/services/api.js` | Axios клиент с Bearer токеном |

---

## Установка

### 1. Миграция базы данных

```bash
cd backend
alembic upgrade head
```

Это создаст таблицу `system_settings` и добавит `panel_api_token` в `gusto_servers`.

### 2. Получите API Token из 3x-ui

1. Откройте панель 3x-ui → **Settings → API Token**
2. Скопируйте токен
3. Вставьте в `panel_api_token` для каждого сервера (через админ-панель или SQL)

### 3. Запустите backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Запустите admin-panel

```bash
cd admin-panel
npm install
npm start
# или для production:
npm run build
```

### 5. Откройте админ-панель

Перейдите на `http://localhost:3000/settings` — откроется страница с 6 табами.

---

## Как пользоваться админ-панелью

### Бот
- Введите **Bot Token** от @BotFather
- Добавьте **ID администраторов** (через запятую)
- Настройте **welcome message**
- Сохраните — бот автоматически подхватит новый токен (без перезапуска!)

### Платежи
- Включите нужные провайдеры (тоггл)
- Введите токены/ключи
- Нажмите **"Проверить подключение"** — система проверит валидность токена
- Сохраните — платежи сразу начнут работать

### Рефералка
- Включите/выключите
- Настройте % для 3 уровней
- Установите минимальную сумму для вывода
- Превью покажет расчет в реальном времени

### Антифрод
- Включите автоматический бан за sharing
- Настройте лимиты IP и стран
- Установите время бана

### Уведомления
- Включите уведомления за 3/1/0 дней до истечения
- Установите порог низкого трафика
- Укажите ID канала для массовых уведомлений

### Система
- Измените название приложения
- Загрузите URL логотипа
- Включите **Maintenance Mode** (технические работы)

---

## API Endpoints

```
GET    /api/settings/                    # Получить все настройки
PUT    /api/settings/                    # Обновить (любую группу)
PATCH  /api/settings/bot                 # Только бот
PATCH  /api/settings/payments            # Только платежи
PATCH  /api/settings/referral          # Только рефералка
PATCH  /api/settings/antifraud         # Только антифрод
PATCH  /api/settings/notifications     # Только уведомления
PATCH  /api/settings/system            # Только система
GET    /api/settings/payments/{provider}/config  # Конфиг провайдера
POST   /api/settings/payments/{provider}/test      # Тест подключения
GET    /api/settings/health              # Публичный health check
```

---

## Как это работает

1. **ConfigService** читает настройки из `system_settings` (PostgreSQL)
2. Результат кэшируется в **Redis** на 5 минут
3. При изменении через админ-панель — кэш инвалидируется
4. **Payments v2** читают токены через `ConfigService` вместо `os.environ`
5. **Bot** при старте загружает токен из `ConfigService`
6. **Background tasks** читают настройки уведомлений/антифрода из `ConfigService`

---

## Важно

- **Не храните `.env` с токенами в репозитории** — теперь всё в БД
- **Сделайте бэкап `system_settings`** — это критичные данные
- **Первый запуск**: создайте запись в `system_settings` (миграция делает это автоматически)
- **Redis обязателен** для кэширования (уже есть в docker-compose)

---

## Обновление существующего проекта

```bash
# 1. Замените файлы
cp backend/app/models/settings.py your-project/backend/app/models/
cp backend/app/services/config_service.py your-project/backend/app/services/
cp backend/app/routers/settings.py your-project/backend/app/routers/
cp backend/app/routers/payments_v2.py your-project/backend/app/routers/payments.py
cp alembic/versions/001_replace_panel_creds_with_token.py your-project/alembic/versions/
cp -r admin-panel/src/views/* your-project/admin-panel/src/views/
cp admin-panel/src/services/api.js your-project/admin-panel/src/services/

# 2. Обновите models/__init__.py — добавьте SystemSettings
# 3. Обновите main.py — добавьте router settings
# 4. Запустите миграцию
alembic upgrade head

# 5. Запустите
make dev
```
