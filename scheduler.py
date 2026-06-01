"""
scheduler.py — запускает бота в режиме ожидания воскресенья.
Каждое воскресенье в SCHEDULE_HOUR (UTC) бот присылает уведомление,
пользователь подтверждает командой /confirm, и запускается сбор + summarize.

Команды бота:
  /start    — приветствие
  /confirm  — подтверждение и запуск дайджеста
  /run      — принудительный запуск (без ожидания воскресенья)
  /status   — информация о следующем запуске
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from telegram_reader import collect_all_chats
from openrouter_client import summarize_chat
from bot_sender import send_summaries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def next_schedule_dt() -> datetime:
    """Возвращает ближайший datetime для автоматического запуска (UTC)."""
    now = datetime.now(timezone.utc)
    days_ahead = config.SCHEDULE_DAY_OF_WEEK - now.weekday()
    if days_ahead < 0 or (days_ahead == 0 and now.hour >= config.SCHEDULE_HOUR):
        days_ahead += 7
    target = now.replace(hour=config.SCHEDULE_HOUR, minute=0, second=0, microsecond=0)
    target += timedelta(days=days_ahead)
    return target


async def run_pipeline(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Основной pipeline: чтение → summarize → отправка."""
    bot = context.bot
    chat_id = config.TARGET_CHAT_ID

    await bot.send_message(chat_id=chat_id, text="⏳ Начинаю сбор сообщений за последние 7 дней...")

    since = datetime.now(timezone.utc) - timedelta(days=7)

    try:
        all_messages = await collect_all_chats(since)
    except Exception as e:
        logger.error(f"Ошибка при сборе сообщений: {e}")
        await bot.send_message(chat_id=chat_id, text=f"❌ Ошибка при сборе сообщений: {e}")
        return

    await bot.send_message(
        chat_id=chat_id,
        text=f"📥 Собрано сообщений: " + ", ".join(
            f"{name}: {len(msgs)}" for name, msgs in all_messages.items()
        ) + "\n\n🤖 Отправляю в ИИ для анализа..."
    )

    summaries = {}
    for chat_name, messages in all_messages.items():
        try:
            await bot.send_message(chat_id=chat_id, text=f"🔄 Анализирую чат: *{chat_name}*...", parse_mode="Markdown")
            summary = await summarize_chat(chat_name, messages)
            summaries[chat_name] = summary
        except Exception as e:
            logger.error(f"Ошибка при summarize {chat_name}: {e}")
            summaries[chat_name] = f"❌ Не удалось сгенерировать summary: {e}"

    await send_summaries(summaries)
    await bot.send_message(chat_id=chat_id, text="✅ Дайджест готов!")


# ─── Обработчики команд ───────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    next_dt = next_schedule_dt()
    await update.message.reply_text(
        f"👋 Привет! Я бот еженедельного дайджеста.\n\n"
        f"⏰ Следующий автоматический запуск: {next_dt.strftime('%d.%m.%Y %H:%M')} UTC\n\n"
        f"Команды:\n"
        f"  /confirm — подтвердить и запустить дайджест\n"
        f"  /run — принудительный немедленный запуск\n"
        f"  /status — статус следующего запуска"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    next_dt = next_schedule_dt()
    delta = next_dt - datetime.now(timezone.utc)
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes = remainder // 60
    await update.message.reply_text(
        f"📅 Следующий запуск: {next_dt.strftime('%d.%m.%Y %H:%M')} UTC\n"
        f"⏳ До запуска: {hours}ч {minutes}мин"
    )


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Подтверждено! Запускаю сбор дайджеста...")
    await run_pipeline(context)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚀 Принудительный запуск дайджеста...")
    await run_pipeline(context)


# ─── Автоматическое уведомление по расписанию ────────────────────────────────

async def weekly_notify(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Присылает уведомление с предложением подтвердить запуск."""
    await context.bot.send_message(
        chat_id=config.TARGET_CHAT_ID,
        text=(
            "🔔 Наступило воскресенье! Готов собрать еженедельный дайджест.\n\n"
            "Нажми /confirm чтобы запустить, или /run для немедленного старта."
        ),
    )


def main() -> None:
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("confirm", cmd_confirm))
    app.add_handler(CommandHandler("run", cmd_run))

    # Еженедельный джоб: каждое воскресенье в SCHEDULE_HOUR:00 UTC
    job_queue = app.job_queue
    job_queue.run_daily(
        weekly_notify,
        time=__import__("datetime").time(
            hour=config.SCHEDULE_HOUR,
            minute=0,
            second=0,
            tzinfo=timezone.utc,
        ),
        days=(config.SCHEDULE_DAY_OF_WEEK,),
    )

    logger.info(
        f"Бот запущен. Еженедельный дайджест: "
        f"день {config.SCHEDULE_DAY_OF_WEEK}, {config.SCHEDULE_HOUR:02d}:00 UTC"
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
