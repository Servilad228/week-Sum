"""
config.py — загрузка конфигурации из .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise ValueError(f"Missing required env variable: {key}")
    return val


def _parse_chats(raw: str) -> list:
    """Парсит строку SOURCE_CHATS → список username/int."""
    result = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.append(int(item))
        except ValueError:
            result.append(item)  # username вида @chan или chan
    return result


# Telethon (user account)
API_ID = int(_require("TELEGRAM_API_ID"))
API_HASH = _require("TELEGRAM_API_HASH")
PHONE = _require("TELEGRAM_PHONE")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "session")

# Bot
BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")

# OpenRouter
OPENROUTER_API_KEY = _require("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-preview")

# Чат для отправки итогов
raw_target = _require("TARGET_CHAT_ID")
try:
    TARGET_CHAT_ID = int(raw_target)
except ValueError:
    TARGET_CHAT_ID = raw_target  # @username

# Список исходных чатов
SOURCE_CHATS = _parse_chats(_require("SOURCE_CHATS"))

# Расписание
SCHEDULE_DAY_OF_WEEK = int(os.getenv("SCHEDULE_DAY_OF_WEEK", "6"))  # 0=пн, 6=вс
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "9"))

# Промпт
CUSTOM_PROMPT = os.getenv("CUSTOM_PROMPT", "").strip()

# Лимиты
MAX_TOKENS_PER_CHUNK = int(os.getenv("MAX_TOKENS_PER_CHUNK", "80000"))
