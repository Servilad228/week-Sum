import asyncio
import os
import sys
import logging
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError
)
from dotenv import load_dotenv

# Включаем подробное логирование Telethon
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_auth")

load_dotenv()

async def main():
    api_id_str = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    session_name = os.getenv('TELEGRAM_SESSION_NAME', 'session')

    print("=== ДИАГНОСТИКА АВТОРИЗАЦИИ ===")
    print(f"API_ID: {api_id_str}")
    print(f"API_HASH: {api_hash}")
    print(f"PHONE: {phone}")
    print(f"SESSION: {session_name}")
    print("==============================")

    if not api_id_str or not api_hash or not phone:
        print("❌ Ошибка: В .env файле отсутствуют нужные настройки!")
        return

    try:
        api_id = int(api_id_str)
    except ValueError:
        print("❌ Ошибка: TELEGRAM_API_ID должен быть числом!")
        return

    client = TelegramClient(session_name, api_id, api_hash)

    print("→ Подключаюсь к Telegram...")
    await client.connect()
    print("✅ Подключение установлено.")

    # Проверяем, авторизованы ли мы уже
    if await client.is_user_authorized():
        print("✅ Вы уже авторизованы!")
        return

    print(f"→ Запрашиваю код на номер {phone}...")
    try:
        # Отправляем код и смотрим на результат
        result = await client.send_code_request(phone)
        print(f"📩 Ответ Telegram: Код отправлен!")
        print(f"   Способ отправки (тип): {type(result.type).__name__}")
        print(f"   Подробности типа: {result.type}")
        print("Проверь Telegram (или SMS).")
        
        # Запрашиваем код из консоли
        code = input("Введите код, который вы получили: ")
        
        try:
            await client.sign_in(phone, code)
            print("✅ Авторизация успешна!")
        except SessionPasswordNeededError:
            # Если включен 2FA (двухфакторная аутентификация)
            password = input("Введите пароль двухфакторной аутентификации (2FA): ")
            await client.sign_in(password=password)
            print("✅ Авторизация успешна (с 2FA)!")
            
    except ApiIdInvalidError:
        print("❌ Ошибка: Неверный TELEGRAM_API_ID или TELEGRAM_API_HASH!")
    except PhoneNumberInvalidError:
        print("❌ Ошибка: Неверный формат номера телефона TELEGRAM_PHONE!")
    except Exception as e:
        print(f"❌ Непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
