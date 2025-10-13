# main.py - с новой функциональностью
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

from database import add_user, remove_user, get_user_count, add_documents, get_recent_documents, get_document_count
from parsers.simple_parser import SimpleParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    try:
        BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не найден")
            return
        
        logger.info("✅ Токен найден, запускаем бота...")
        
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
        dp = Dispatcher()
        parser = SimpleParser()

        @dp.message(Command("start"))
        async def start_command(message: types.Message):
            user_id = message.from_user.id
            add_user(user_id)
            user_count = get_user_count()
            doc_count = get_document_count()
            
            await message.answer(
                "👋 <b>Добро пожаловать в бот правовых актов!</b>\n\n"
                "✅ Вы подписаны на обновления\n"
                f"📊 Пользователей: {user_count}\n"
                f"📄 Документов в базе: {doc_count}\n\n"
                "⚡ <b>Новые команды:</b>\n"
                "/docs - последние документы\n"
                "/update - обновить базу\n"
                "/stats - статистика\n"
                "/help - справка"
            )

        @dp.message(Command("docs"))
        async def docs_command(message: types.Message):
            """Показывает последние документы"""
            documents = get_recent_documents(5)
            if not documents:
                await message.answer("📭 В базе пока нет документов. Используйте /update для загрузки.")
                return
            
            await message.answer(f"📄 <b>Последние документы:</b>")
            for doc in documents:
                text = (
                    f"<b>{doc.get('organization', 'Организация')}</b>\n"
                    f"📅 {doc.get('publishDate', 'Дата')}\n"
                    f"<i>{doc.get('documentTitle', 'Без названия')}</i>\n"
                    f"<a href='{doc.get('url', '')}'>📄 Открыть</a>"
                )
                await message.answer(text)
                await asyncio.sleep(0.3)

        @dp.message(Command("update"))
        async def update_command(message: types.Message):
            """Обновляет базу документов"""
            await message.answer("🔄 Загрузка новых документов...")
            try:
                new_docs = parser.get_documents()
                if new_docs:
                    added_count = add_documents(new_docs)
                    if added_count > 0:
                        await message.answer(f"✅ Добавлено {added_count} новых документов!")
                    else:
                        await message.answer("✅ Новых документов не найдено")
                else:
                    await message.answer("❌ Не удалось загрузить документы")
            except Exception as e:
                logger.error(f"Ошибка обновления: {e}")
                await message.answer("❌ Ошибка при обновлении базы")

        @dp.message(Command("stats"))
        async def stats_command(message: types.Message):
            user_count = get_user_count()
            doc_count = get_document_count()
            await message.answer(
                "📊 <b>Статистика бота:</b>\n\n"
                f"• Пользователей: {user_count}\n"
                f"• Документов: {doc_count}\n"
                f"• Статус: 🟢 Активен\n"
                f"• Платформа: bothost.ru"
            )

        @dp.message(Command("help"))
        async def help_command(message: types.Message):
            await message.answer(
                "ℹ️ <b>Справка:</b>\n\n"
                "/start - подписаться\n"
                "/docs - последние документы\n" 
                "/update - обновить базу\n"
                "/stats - статистика\n"
                "/unsubscribe - отписаться"
            )

        @dp.message(Command("unsubscribe"))
        async def unsubscribe_command(message: types.Message):
            user_id = message.from_user.id
            remove_user(user_id)
            await message.answer("🔔 Вы отписаны от обновлений")

        @dp.message()
        async def echo(message: types.Message):
            await message.answer("ℹ️ Используйте /help для списка команд")

        logger.info("🚀 Бот запущен с обновленной функциональностью!")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())