# main.py - с базой данных пользователей
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

from database import add_user, remove_user, get_user_count

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    try:
        # Получаем токен из переменных окружения bothost.ru
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не найден")
            return
        
        logger.info("✅ Токен найден, запускаем бота...")
        
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        dp = Dispatcher()

        @dp.message(Command("start"))
        async def start_command(message: types.Message):
            user_id = message.from_user.id
            add_user(user_id)
            user_count = get_user_count()
            
            await message.answer(
                "👋 <b>Добро пожаловать в бот правовых актов!</b>\n\n"
                "✅ Вы подписаны на обновления\n"
                f"📊 Всего пользователей: {user_count}\n\n"
                "⚡ <b>Доступные команды:</b>\n"
                "/help - справка\n"
                "/stats - статистика\n"
                "/unsubscribe - отписаться"
            )

        @dp.message(Command("help"))
        async def help_command(message: types.Message):
            await message.answer(
                "ℹ️ <b>Справка по боту:</b>\n\n"
                "📋 <b>Основные команды:</b>\n"
                "/start - подписаться и начать работу\n"
                "/stats - статистика бота\n"
                "/unsubscribe - отписаться от обновлений\n\n"
                "🔔 <b>В разработке:</b>\n"
                "• Автоматические уведомления о новых документах\n"
                "• Поиск по правовым актам\n"
                "• Отслеживание изменений законодательства"
            )

        @dp.message(Command("stats"))
        async def stats_command(message: types.Message):
            user_count = get_user_count()
            await message.answer(
                "📊 <b>Статистика бота:</b>\n\n"
                f"• Пользователей: {user_count}\n"
                f"• Статус: 🟢 Активен\n"
                f"• Платформа: bothost.ru\n\n"
                "⚡ Бот работает стабильно"
            )

        @dp.message(Command("unsubscribe"))
        async def unsubscribe_command(message: types.Message):
            user_id = message.from_user.id
            remove_user(user_id)
            await message.answer(
                "🔔 Вы отписаны от обновлений.\n"
                "Чтобы снова подписаться, отправьте /start"
            )

        @dp.message()
        async def echo(message: types.Message):
            await message.answer(
                "ℹ️ Используйте команды:\n"
                "/start - начать работу\n"
                "/help - справка\n"
                "/stats - статистика"
            )

        logger.info("🚀 Бот запускается с обновленной функциональностью...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())