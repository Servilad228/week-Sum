# 📊 Telegram Weekly Summarizer

Бот собирает сообщения из указанных Telegram-чатов за последние 7 дней, отправляет их в **Gemini 2.5 Flash** через OpenRouter и присылает итоговый дайджест в нужный чат.

---

## Архитектура

```
Telethon (user account)  →  читает сообщения из чатов
       ↓
OpenRouter (Gemini 2.5 Flash)  →  генерирует summary
       ↓
Telegram Bot API  →  отправляет итог в TARGET_CHAT_ID
```

- **Telethon** — читает историю любых чатов, где ты состоишь
- **python-telegram-bot** — бот с командами и планировщиком
- **OpenRouter** — прокси к Gemini 2.5 Flash

---

## Быстрый старт (Debian 13)

### 1. Клонировать проект на сервер

```bash
scp -r . root@your-server:/opt/week-summarizer
# или git clone
```

### 2. Настроить переменные окружения

```bash
cd /opt/week-summarizer
cp .env.example .env
nano .env
```

Заполни все поля (см. ниже).

### 3. Развернуть

```bash
bash deploy.sh
```

Скрипт:
1. Создаст virtualenv и установит зависимости
2. Запросит авторизацию в Telegram (телефон + код из SMS) — **один раз**
3. Установит systemd-сервис и запустит бота

---

## Переменные окружения (`.env`)

| Переменная | Описание |
|---|---|
| `TELEGRAM_API_ID` | App API ID с [my.telegram.org](https://my.telegram.org) |
| `TELEGRAM_API_HASH` | App API Hash оттуда же |
| `TELEGRAM_PHONE` | Твой номер телефона (+7...) |
| `TELEGRAM_SESSION_NAME` | Имя файла сессии (по умолчанию `session`) |
| `TELEGRAM_BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/botfather) |
| `OPENROUTER_API_KEY` | Ключ с [openrouter.ai](https://openrouter.ai) |
| `OPENROUTER_MODEL` | Модель (по умолчанию `google/gemini-2.5-flash-preview`) |
| `TARGET_CHAT_ID` | Куда слать итог: `@username` или числовой ID |
| `SOURCE_CHATS` | Откуда читать: `@chat1,@chat2,-1001234567890` |
| `SCHEDULE_DAY_OF_WEEK` | День недели (0=пн, 6=вс, по умолчанию `6`) |
| `SCHEDULE_HOUR` | Час UTC (по умолчанию `9`) |
| `CUSTOM_PROMPT` | Свой промпт (если пусто — берётся из `prompts/summary_prompt.txt`) |
| `MAX_TOKENS_PER_CHUNK` | Макс. токенов на чанк (по умолчанию `80000`) |

### Как получить Telegram API ID/Hash

1. Перейди на [my.telegram.org](https://my.telegram.org)
2. Войди в аккаунт
3. "API development tools" → создай приложение
4. Скопируй `App api_id` и `App api_hash`

---

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие + время следующего запуска |
| `/status` | Когда следующий автоматический дайджест |
| `/confirm` | Подтвердить и запустить сборку прямо сейчас |
| `/run` | Принудительный запуск без подтверждения |

---

## Промпт

Промпт хранится в `prompts/summary_prompt.txt`. Ты можешь:
- Отредактировать файл под свои нужды
- Или задать промпт прямо в `.env` через `CUSTOM_PROMPT`

Доступные плейсхолдеры: `{chat_name}`, `{message_count}`, `{date_generated}`, `{messages}`

---

## Структура проекта

```
week Sum/
├── .env.example          # Шаблон переменных окружения
├── .gitignore
├── config.py             # Загрузка конфигурации
├── telegram_reader.py    # Чтение сообщений через Telethon
├── openrouter_client.py  # Запросы к OpenRouter / chunking
├── bot_sender.py         # Отправка результата через Bot API
├── scheduler.py          # Основной бот с планировщиком
├── requirements.txt
├── deploy.sh             # Деплой на Debian
├── week-summarizer.service  # Systemd unit
└── prompts/
    └── summary_prompt.txt   # Промпт по умолчанию
```

---

## Логи

```bash
journalctl -u week-summarizer -f
```
