# Шальной — дерзкий AI-бот для Telegram

Полноценный асинхронный Telegram-бот для взрослого сообщества 18+. Пометка означает мат,
взрослый юмор, разговоры об отношениях, алкоголе и вечеринках. Проект не предназначен для
порнографии, сексуального контента, незаконных материалов или контента с несовершеннолетними.

## Возможности

- живые AI-ответы по упоминанию, ответу, триггеру и регулируемой случайности;
- четыре уровня характера и отдельное включение мата для каждого чата;
- краткосрочный контекст и долгосрочная память с добровольным удалением;
- Edge TTS и Telegram voice в OGG/Opus, подготовлена точка расширения для ElevenLabs;
- безопасная медиатека на Telegram `file_id`, локальных файлах или разрешённых URL;
- мемы, GIF, фото, реакции, разнообразные приветствия;
- рулетка, «Кто сегодня», дуэль, правда или действие, прогноз, оценка и безопасный roast;
- планировщик одноразовых, ежедневных и еженедельных публикаций;
- админ-меню, локальные настройки чата, блокировка доступа к боту, статистика и healthcheck;
- polling для разработки и webhook для production;
- PostgreSQL, Redis с in-memory fallback, SQLAlchemy 2, Alembic, Docker и GitHub Actions.

## Стек и требования

- Python 3.12;
- Docker Engine и Docker Compose — рекомендуемый вариант;
- PostgreSQL 16+, Redis 7+;
- `ffmpeg` для конвертации голосовых;
- токен Telegram и ключ OpenAI-совместимого AI API.

## 1. Создание бота через BotFather

1. Откройте [@BotFather](https://t.me/BotFather) и отправьте `/newbot`.
2. Укажите имя и username, который заканчивается на `bot`.
3. Скопируйте выданный токен в локальный `.env` как `BOT_TOKEN`. Никогда не отправляйте его
   в чат, issue или коммит.
4. Выполните `/setprivacy`, выберите бота и нажмите `Disable`, иначе бот не увидит обычные
   сообщения группы.
5. Через `/setjoingroups` разрешите добавление в группы.
6. Через `/setcommands` при желании задайте команды; приложение также установит их само.

Если токен где-либо публиковался, используйте `/revoke`, а затем `/token` и создайте новый.

## 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Минимально заполните:

```dotenv
BOT_TOKEN=новый_токен_из_BotFather
BOT_USERNAME=username_без_собаки
SUPERADMIN_IDS=123456789
AI_PROVIDER=openai
AI_API_KEY=ключ_провайдера
AI_MODEL=gpt-4.1-mini
```

Telegram ID можно узнать у `@userinfobot`. Несколько `SUPERADMIN_IDS` перечисляются через
запятую. `.env` исключён из Git.

### Все переменные

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | Токен Telegram, обязателен |
| `BOT_USERNAME` | Username бота без `@` |
| `SUPERADMIN_IDS` | Положительные Telegram ID через запятую |
| `DATABASE_URL` | Async SQLAlchemy URL PostgreSQL |
| `REDIS_URL` | URL Redis; пустое значение включает memory fallback |
| `AI_PROVIDER` | `openai`, `openrouter`, `compatible` или `ollama` |
| `AI_API_KEY` | Ключ AI API; для Ollama может быть пустым |
| `AI_BASE_URL` | URL OpenAI-совместимого API |
| `AI_MODEL` | Модель провайдера |
| `AI_TEMPERATURE` | Температура от 0 до 2 |
| `AI_MAX_TOKENS` | Максимум токенов ответа |
| `DEFAULT_TIMEZONE` | По умолчанию `Europe/Berlin` |
| `BOT_MODE` | `polling` или `webhook` |
| `WEBHOOK_URL` | Публичный HTTPS-домен без конечного пути |
| `WEBHOOK_SECRET` | Случайная секретная строка webhook |
| `PORT` | HTTP-порт healthcheck/webhook |
| `LOG_LEVEL` | `INFO`, `WARNING`, `DEBUG` |
| `TTS_PROVIDER` | Сейчас рабочее значение `edge` |
| `TTS_VOICE` | Например `ru-RU-DmitryNeural` |
| `DEFAULT_RUDENESS_LEVEL` | От 1 до 4 |
| `DEFAULT_SWEARING_ENABLED` | Включение мата |
| `DEFAULT_RANDOM_REPLY_CHANCE` | Вероятность случайного ответа 0–100 |
| `DEFAULT_VOICE_REPLY_CHANCE` | Вероятность voice 0–100 |
| `DEFAULT_REACTION_CHANCE` | Вероятность реакции 0–100 |

## 3. Запуск через Docker

В `.env` для Compose оставьте:

```dotenv
DATABASE_URL=postgresql+asyncpg://bot:bot@postgres:5432/cheeky_bot
REDIS_URL=redis://redis:6379/0
BOT_MODE=polling
```

Запуск:

```bash
docker compose up --build -d
docker compose logs -f bot
```

Миграции запускаются контейнером автоматически. Остановка:

```bash
docker compose down
```

Данные PostgreSQL и Redis находятся в именованных Docker volumes и не удаляются обычным
`down`.

## 4. Локальный запуск без Docker

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install ".[dev]"
alembic upgrade head
python -m app.main
```

Для локальной SQLite-проверки можно установить
`DATABASE_URL=sqlite+aiosqlite:///./cheeky_bot.db`, но production должен использовать PostgreSQL.

## 5. PostgreSQL, Redis и миграции

Только инфраструктура:

```bash
docker compose up -d postgres redis
alembic upgrade head
alembic current
```

Новая миграция после изменения моделей:

```bash
alembic revision --autogenerate -m "описание"
alembic upgrade head
```

## 6. Настройка AI API

OpenAI:

```dotenv
AI_PROVIDER=openai
AI_API_KEY=...
AI_BASE_URL=
AI_MODEL=gpt-4.1-mini
```

OpenRouter:

```dotenv
AI_PROVIDER=openrouter
AI_API_KEY=...
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openai/gpt-4.1-mini
```

Локальный Ollama:

```dotenv
AI_PROVIDER=ollama
AI_API_KEY=
AI_BASE_URL=http://host.docker.internal:11434/v1
AI_MODEL=qwen3:8b
```

Бизнес-логика зависит от абстракции `AIProvider`, а не от конкретного SDK. При недоступности
провайдера бот повторяет временные ошибки и возвращает резервную смешную фразу.

## 7. Edge TTS

Edge TTS не требует отдельного ключа. Нужен `ffmpeg`. Доступные в интерфейсе голоса:

- `ru-RU-DmitryNeural`;
- `ru-RU-SvetlanaNeural`;
- `uk-UA-OstapNeural`;
- `de-DE-ConradNeural`;
- `en-US-GuyNeural`.

Администратор меняет голос командой `/voice_settings`. Временные MP3/OGG удаляются после
отправки даже при ошибке Telegram.

## 8. Добавление в группу

1. Добавьте бота в Telegram-группу.
2. Выдайте право отправлять сообщения, медиа, опросы и реакции.
3. Для приветствий разрешите видеть события о новых участниках.
4. Убедитесь, что Privacy Mode отключён в BotFather.
5. Отправьте `/admin` из аккаунта администратора группы.

## 9. Команды пользователей

`/start`, `/help`, `/profile`, `/memory`, `/forget_me`, `/voice`, `/meme`, `/gif`, `/photo`,
`/reaction`, `/roulette`, `/who_today`, `/duel`, `/truth_or_dare`, `/prediction`, `/rate`,
`/roast`, `/birthday`, `/settings`.

## 10. Команды администраторов

`/admin`, `/personality`, `/rudeness`, `/swearing`, `/voice_settings`, `/media_settings`,
`/auto_reply`, `/reaction_settings`, `/schedule`, `/schedule_delete`, `/stats`, `/users`,
`/ban_bot`, `/unban_bot`, `/reset_context`, `/broadcast`, `/logs`, `/health`, `/add_media`,
`/delete_media`, `/media_stats`.

Рассылка доступна только `SUPERADMIN_IDS` и требует явного `--confirm`.

## 11. Polling и webhook

Polling подходит локальной разработке и Railway worker. При нём приложение всё равно поднимает
`GET /health`.

Webhook:

```dotenv
BOT_MODE=webhook
WEBHOOK_URL=https://example.com
WEBHOOK_SECRET=длинная_случайная_строка
```

Telegram endpoint формируется как `WEBHOOK_URL/telegram/webhook`. Секрет проверяется через
заголовок Telegram.

## 12. GitHub и CI

```bash
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/USER/cheeky-telegram-bot.git
git push -u origin main
```

Workflow на push и pull request запускает Ruff, проверку форматирования, mypy и pytest. Реальные
секреты в GitHub Actions не нужны.

## 13. Railway

1. Создайте проект из GitHub-репозитория.
2. Добавьте сервисы PostgreSQL и Redis.
3. В Variables добавьте все значения из `.env.example`; ссылки на БД возьмите из Railway
   variables и приведите PostgreSQL URL к `postgresql+asyncpg://` (код также нормализует обычный
   `postgresql://`).
4. Для первого запуска проще установить `BOT_MODE=polling`.
5. Railway распознает `railway.json` и Dockerfile, выполнит миграции и проверит `/health`.
6. После успешного deploy откройте logs и убедитесь, что есть `bot_started`.

Никогда не добавляйте Telegram/AI-ключи в GitHub. Они вводятся только в Railway Variables.

## 14. Render

Создайте Web Service из репозитория, выберите Docker, добавьте PostgreSQL/Redis и переменные.
Используйте polling или публичный URL Render как `WEBHOOK_URL`. Health Check Path: `/health`.

## 15. Fly.io

Создайте приложение через `fly launch --no-deploy`, подключите Postgres/Redis, добавьте секреты
через `fly secrets set` и выполните `fly deploy`. В production предпочтителен webhook.

## 16. Безопасность и приватность

- ключи читаются только из environment variables и не выводятся в логах;
- админ-права перепроверяются через Telegram или `SUPERADMIN_IDS`;
- ORM использует параметризованные запросы;
- пользовательский текст не становится системным промптом;
- потенциальные prompt-injection инструкции не выполняются;
- бот не запускает код и shell-команды из чата;
- тип и размер медиа валидируются;
- номера, похожие на платёжные данные, маскируются до AI-контекста;
- память удаляется только после inline-подтверждения;
- запрещены сексуальный контент, травля, угрозы и оскорбления защищённых групп.

## 17. Проверки проекта

```bash
ruff check .
ruff format --check .
mypy app
pytest
docker compose config
docker build -t cheeky-telegram-bot .
```

## 18. Частые ошибки

**Unauthorized / invalid token** — токен неверный или отозван. Создайте новый в BotFather.

**Бот видит только команды** — отключите Privacy Mode через `/setprivacy`.

**Connection refused к PostgreSQL/Redis** — внутри Compose используйте хосты `postgres` и
`redis`, а не `localhost`.

**AI отвечает fallback-фразой** — проверьте ключ, model, base URL, квоту и rate limit.

**Нет голосового** — проверьте наличие `ffmpeg`, доступ к сети и название Edge-голоса.

**Webhook не работает** — URL должен быть публичным HTTPS, а `WEBHOOK_SECRET` непустым.

**Миграции не стартуют** — проверьте `DATABASE_URL` и выполните `alembic upgrade head` вручную.

**Railway healthcheck падает** — порт должен читаться из `PORT`; endpoint `/health` доступен в
обоих режимах.

## Структура

```text
app/
├── ai/                 # провайдер, промпты, защита, контекст
├── bot/                # handlers, middleware, filters, keyboards, states
├── config/             # единая конфигурация
├── database/           # модели, сессии, репозитории
├── services/           # AI orchestration, TTS, медиа, игры, scheduler
├── texts/              # русская локализация
├── utils/              # HTML и структурированные логи
└── main.py              # polling/webhook lifecycle
alembic/                 # миграции
tests/                   # unit/integration tests
media/                   # локальная безопасная медиатека
scripts/                 # entrypoint и проверки
```

Лицензия и правила использования выбираются владельцем репозитория.

