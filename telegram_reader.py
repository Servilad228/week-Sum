"""
telegram_reader.py — читает сообщения через пользовательский аккаунт (Telethon)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.tl.types import (
    MessageService,
    User,
    MessageMediaDocument,
    MessageMediaPhoto,
    MessageMediaWebPage,
)

import config

logger = logging.getLogger(__name__)


def _is_bot(sender) -> bool:
    return isinstance(sender, User) and bool(sender.bot)


def _is_media_only(msg) -> bool:
    """Возвращает True, если сообщение — только медиа без текста."""
    if msg.text:
        return False
    if isinstance(msg.media, (MessageMediaDocument, MessageMediaPhoto)):
        return True
    return False


def _format_message(msg, sender_name: str) -> str:
    text = (msg.text or "").strip()
    dt = msg.date.strftime("%Y-%m-%d %H:%M")
    return f"[{dt}] {sender_name}: {text}"


async def fetch_chat_messages(
    client: TelegramClient,
    chat_id,
    since: datetime,
) -> list[str]:
    """
    Собирает все подходящие сообщения из chat_id начиная с `since`.
    Возвращает список строк вида "[дата] Имя: текст".
    """
    messages = []

    async for msg in client.iter_messages(chat_id, offset_date=None, reverse=False):
        # Останавливаемся, если сообщение старше since
        msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
        if msg_date < since:
            break

        # Пропускаем служебные сообщения (вступление/выход/pin и т.д.)
        if isinstance(msg, MessageService):
            continue

        # Пропускаем сообщения без текста (медиа-файлы без подписи)
        if _is_media_only(msg):
            continue

        # Пропускаем сообщения от ботов
        sender = await msg.get_sender()
        if _is_bot(sender):
            continue

        if isinstance(sender, User):
            name = (
                f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                or sender.username
                or "Unknown"
            )
        else:
            name = getattr(sender, "title", "Unknown")

        line = _format_message(msg, name)
        messages.append(line)

    # iter_messages возвращает от новых к старым — разворачиваем
    messages.reverse()
    return messages


async def collect_all_chats(since: datetime) -> dict[str, list[str]]:
    """
    Читает сообщения из всех SOURCE_CHATS за последние 7 дней.
    Возвращает dict { имя_чата: [строки сообщений] }
    """
    results = {}

    async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
        await client.start(phone=config.PHONE)

        for chat_id in config.SOURCE_CHATS:
            try:
                entity = await client.get_entity(chat_id)
                chat_name = getattr(entity, "title", None) or getattr(entity, "username", str(chat_id))
                logger.info(f"Читаю чат: {chat_name} ({chat_id})")
                msgs = await fetch_chat_messages(client, entity, since)
                results[chat_name] = msgs
                logger.info(f"  → Собрано {len(msgs)} сообщений")
            except Exception as e:
                logger.error(f"Ошибка при чтении чата {chat_id}: {e}")
                results[str(chat_id)] = []

    return results
