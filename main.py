# main.py - минимальная версия для bothost.ru
import asyncio
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота для bothost.ru"""
    try:
        # Проверяем конфигурацию
        from config import BOT_TOKEN
        
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не установлен. Проверьте настройки на bothost.ru")
            return
        
        logger.info("✅ Конфигурация загружена успешно")
        
        # Импортируем бота после проверки конфигурации
        from bot.bot_core import bot, dp
        
        logger.info("🚀 Запуск бота на bothost.ru...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())