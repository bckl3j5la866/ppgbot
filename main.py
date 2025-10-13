# main.py - временная версия для теста
import asyncio
import logging
import sys
import os

# Добавьте путь к корневой папке в PYTHONPATH
sys.path.append(os.path.dirname(__file__))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Упрощенная версия для тестирования"""
    try:
        # Импорты внутри функции чтобы избежать циклических импортов
        from bot.bot_core import bot, dp
        
        logger.info("🚀 Запуск Telegram-бота...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())