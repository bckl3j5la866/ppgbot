# main.py
import asyncio
import logging
from bot.bot_core import bot, dp, main as bot_main
from notifier import start_notifier, shutdown_notifier
from performance_optimizations import shutdown_executor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """
    Основная точка входа бота.
    Запускает long polling и службу уведомлений.
    """
    logger.info("🚀 Запуск Telegram-бота и службы уведомлений...")
    
    # Запускаем службу уведомлений в фоновом режиме
    notifier_task = asyncio.create_task(start_notifier())
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен пользователем.")
    finally:
        # Отменяем задачу уведомлений при остановке
        notifier_task.cancel()
        try:
            await notifier_task
        except asyncio.CancelledError:
            logger.info("🛑 Служба уведомлений остановлена")
        
        # Корректно завершаем пул потоков
        await shutdown_executor()
        await shutdown_notifier()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Приложение полностью остановлено.")