"""
bot_sender.py — отправляет итоговые summary через Telegram Bot API.
"""
import logging

import httpx

import config

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{config.BOT_TOKEN}"
MAX_MESSAGE_LEN = 4096  # лимит Telegram


def _split_text(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Разбивает длинный текст на части по max_len символов (по границе строки)."""
    if len(text) <= max_len:
        return [text]

    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        # Ищем последний перенос строки в пределах max_len
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


async def send_message(text: str, chat_id=None, parse_mode: str = "Markdown") -> None:
    """Отправляет текст в указанный чат (по умолчанию TARGET_CHAT_ID)."""
    target = chat_id or config.TARGET_CHAT_ID
    parts = _split_text(text)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for part in parts:
            payload = {
                "chat_id": target,
                "text": part,
                "parse_mode": parse_mode,
            }
            resp = await client.post(f"{TELEGRAM_API_BASE}/sendMessage", json=payload)
            if resp.status_code != 200:
                logger.error(f"Ошибка отправки сообщения: {resp.status_code} {resp.text}")
                resp.raise_for_status()
            logger.info(f"Сообщение ({len(part)} символов) отправлено в {target}")


async def send_summaries(summaries: dict[str, str]) -> None:
    """
    Отправляет все summary чатов в TARGET_CHAT_ID.
    summaries = { имя_чата: текст_summary }
    """
    if not summaries:
        await send_message("ℹ️ Нет данных для отчёта за прошедшую неделю.")
        return

    total = len(summaries)
    for i, (chat_name, summary) in enumerate(summaries.items(), 1):
        header = f"📊 *Отчёт {i}/{total}*\n\n"
        await send_message(header + summary)
