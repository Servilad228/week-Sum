"""
openrouter_client.py — отправляет текст в OpenRouter (Gemini 2.5 Flash)
и возвращает готовый summary.
"""
import logging
import os
from pathlib import Path
from datetime import datetime

import httpx

import config

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Примерное число символов на токен для русского текста
CHARS_PER_TOKEN = 3
MAX_CHARS_PER_CHUNK = config.MAX_TOKENS_PER_CHUNK * CHARS_PER_TOKEN


def _load_prompt_template() -> str:
    if config.CUSTOM_PROMPT:
        return config.CUSTOM_PROMPT

    prompt_path = Path(__file__).parent / "prompts" / "summary_prompt.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    # Fallback минимальный промпт
    return (
        "Ты — аналитик Telegram-переписки. Сделай краткое резюме переписки за неделю "
        "из чата «{chat_name}» ({message_count} сообщений) в формате дайджеста. "
        "Дата: {date_generated}.\n\nСООБЩЕНИЯ:\n{messages}"
    )


def _build_prompt(template: str, chat_name: str, messages: list[str]) -> str:
    body = "\n".join(messages)
    return template.format(
        chat_name=chat_name,
        message_count=len(messages),
        date_generated=datetime.now().strftime("%d.%m.%Y"),
        messages=body,
    )


def _split_into_chunks(messages: list[str]) -> list[list[str]]:
    """Разбивает список сообщений на чанки по MAX_CHARS_PER_CHUNK символов."""
    chunks = []
    current_chunk = []
    current_len = 0

    for msg in messages:
        msg_len = len(msg)
        if current_chunk and current_len + msg_len > MAX_CHARS_PER_CHUNK:
            chunks.append(current_chunk)
            current_chunk = []
            current_len = 0
        current_chunk.append(msg)
        current_len += msg_len

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def _call_openrouter(prompt: str) -> str:
    """Отправляет один запрос в OpenRouter и возвращает текст ответа."""
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/week-summarizer",
        "X-Title": "Week Summarizer",
    }
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def summarize_chat(chat_name: str, messages: list[str]) -> str:
    """
    Суммаризирует сообщения одного чата.
    Если сообщений много — разбивает на чанки, суммаризирует каждый,
    затем делает финальный summary из промежуточных.
    """
    if not messages:
        return f"📋 **{chat_name}**: за прошедшую неделю сообщений не было."

    template = _load_prompt_template()
    chunks = _split_into_chunks(messages)

    logger.info(f"Чат '{chat_name}': {len(messages)} сообщений → {len(chunks)} чанков")

    if len(chunks) == 1:
        prompt = _build_prompt(template, chat_name, messages)
        return await _call_openrouter(prompt)

    # Несколько чанков: суммаризируем каждый, потом объединяем
    partial_summaries = []
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"  Обрабатываю чанк {i}/{len(chunks)} ({len(chunk)} сообщений)...")
        chunk_name = f"{chat_name} [часть {i}/{len(chunks)}]"
        prompt = _build_prompt(template, chunk_name, chunk)
        partial = await _call_openrouter(prompt)
        partial_summaries.append(partial)

    # Финальный merge-промпт
    merge_prompt = (
        f"Ты — аналитик. Ниже приведены промежуточные резюме переписки из чата «{chat_name}» "
        f"за неделю. Объедини их в единый краткий дайджест, убери повторы.\n\n"
        + "\n\n---\n\n".join(partial_summaries)
    )
    logger.info(f"  Объединяю {len(partial_summaries)} промежуточных summary...")
    return await _call_openrouter(merge_prompt)
