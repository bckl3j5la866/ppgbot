# main.py - работающая версия без парсера
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

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
            await message.answer(
                "👋 <b>Бот успешно запущен!</b>\n\n"
                "✅ Система работает корректно\n"
                "📚 Функционал парсера будет добавлен позже\n"
                "🤖 Бот готов к базовым командам"
            )

        @dp.message(Command("help"))
        async def help_command(message: types.Message):
            await message.answer(
                "ℹ️ <b>Доступные команды:</b>\n"
                "/start - запуск бота\n"
                "/help - справка\n"
                "/test - тест работы"
            )

        @dp.message(Command("test"))
        async def test_command(message: types.Message):
            await message.answer("✅ Тестовое сообщение - бот работает!")

        @dp.message()
        async def echo(message: types.Message):
            await message.answer("ℹ️ Используйте /start или /help")

        logger.info("🚀 Бот запускается...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())