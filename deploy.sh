#!/bin/bash
# deploy.sh — развёртывание на Debian 13 сервере
# Запускать от root: bash deploy.sh

set -e

PROJECT_DIR="/opt/week-summarizer"
SERVICE_NAME="week-summarizer"

echo "=== Week Summarizer — деплой ==="

# 1. Создать директорию
mkdir -p "$PROJECT_DIR"
cp -r ./* "$PROJECT_DIR/"
cd "$PROJECT_DIR"

# 2. Создать виртуальное окружение
echo "→ Создаю venv..."
python3 -m venv venv
source venv/bin/activate

# 3. Установить зависимости
echo "→ Устанавливаю зависимости..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Проверить наличие .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Создан .env из шаблона. Заполни переменные: nano $PROJECT_DIR/.env"
    echo "    Затем запусти: systemctl start $SERVICE_NAME"
    exit 0
fi

# 5. Первый запуск Telethon (авторизация)
echo "→ Авторизация Telethon (нужен телефон и код из SMS)..."
python3 -c "
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import os
load_dotenv()
client = TelegramClient(os.getenv('TELEGRAM_SESSION_NAME','session'), int(os.getenv('TELEGRAM_API_ID')), os.getenv('TELEGRAM_API_HASH'))
asyncio.run(client.start(phone=os.getenv('TELEGRAM_PHONE')))
print('✅ Сессия сохранена')
"

# 6. Установить systemd-сервис
echo "→ Устанавливаю systemd-сервис..."
cp week-summarizer.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo ""
echo "✅ Готово! Статус: systemctl status $SERVICE_NAME"
echo "📋 Логи: journalctl -u $SERVICE_NAME -f"
