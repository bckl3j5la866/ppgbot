# main.py - с новым WebParser
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# Импорты из database.py
from database import (
    add_user, remove_user, get_user_count, 
    add_documents, get_recent_documents, get_document_count
)

# Импорты нового парсера
from parsers.web_parser import get_parser

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
        parser = get_parser()

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
                "⚡ <b>Команды:</b>\n"
                "/docs - последние документы\n"
                "/update - обновить базу\n"
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
                "/docs - показать последние документы\n"
                "/update - обновить базу документов\n"
                "/stats - статистика бота\n"
                "/unsubscribe - отписаться от обновлений\n\n"
                "🔔 <b>Источники:</b>\n"
                "• Минпросвещения России\n"
                "• Минобрнауки Якутии\n"
                "• Рособрнадзор"
            )

        @dp.message(Command("stats"))
        async def stats_command(message: types.Message):
            user_count = get_user_count()
            doc_count = get_document_count()
            recent_docs = get_recent_documents(3)
            
            stats_text = (
                "📊 <b>Статистика бота:</b>\n\n"
                f"• Пользователей: {user_count}\n"
                f"• Документов: {doc_count}\n"
                f"• Статус: 🟢 Активен\n"
                f"• Парсер: WebParser\n\n"
            )
            
            if recent_docs:
                stats_text += "📅 <b>Последние документы:</b>\n"
                for doc in recent_docs:
                    org_short = doc['organization'].split()[-1]  # Берем последнее слово
                    stats_text += f"• {doc['publishDate']} - {org_short}\n"
            
            await message.answer(stats_text)

        @dp.message(Command("unsubscribe"))
        async def unsubscribe_command(message: types.Message):
            user_id = message.from_user.id
            remove_user(user_id)
            await message.answer(
                "🔔 Вы отписаны от обновлений.\n"
                "Чтобы снова подписаться, отправьте /start"
            )

        @dp.message(Command("docs"))
        async def docs_command(message: types.Message):
            """Показывает последние документы"""
            documents = get_recent_documents(5)
            if not documents:
                await message.answer(
                    "📭 <b>В базе пока нет документов</b>\n\n"
                    "Используйте команду /update для загрузки документов."
                )
                return
            
            await message.answer(f"📄 <b>Последние {len(documents)} документов:</b>")
            
            for i, doc in enumerate(documents, 1):
                # Сокращаем длинное название организации
                org_name = doc['organization']
                if len(org_name) > 40:
                    org_name = org_name[:40] + "..."
                
                text = (
                    f"<b>📋 Документ {i}</b>\n"
                    f"<b>Организация:</b> {org_name}\n"
                    f"<b>Дата:</b> {doc.get('publishDate', 'Не указана')}\n"
                    f"<b>Название:</b> {doc.get('documentTitle', 'Без названия')}\n"
                    f"<a href='{doc.get('url', '')}'>🔗 Открыть документ</a>"
                )
                await message.answer(text)
                await asyncio.sleep(0.3)  # Задержка между сообщениями

        @dp.message(Command("update"))
        async def update_command(message: types.Message):
            """Обновляет базу документов"""
            wait_msg = await message.answer(
                "🔄 <b>Загрузка новых документов...</b>\n\n"
                "Это может занять 1-2 минуты.\n"
                "Парсим официальные источники..."
            )
            
            try:
                new_docs = parser.get_documents()
                if new_docs:
                    added_count = add_documents(new_docs)
                    if added_count > 0:
                        await wait_msg.edit_text(
                            f"✅ <b>Обновление завершено!</b>\n\n"
                            f"Добавлено <b>{added_count}</b> новых документов.\n"
                            f"Всего в базе: <b>{get_document_count()}</b>\n\n"
                            f"Используйте /docs для просмотра"
                        )
                    else:
                        await wait_msg.edit_text(
                            "✅ <b>Все документы актуальны</b>\n\n"
                            "Новых документов не найдено.\n"
                            f"Всего в базе: <b>{get_document_count()}</b>"
                        )
                else:
                    await wait_msg.edit_text(
                        "❌ <b>Не удалось загрузить документы</b>\n\n"
                        "Возможно, проблема с доступом к источникам.\n"
                        "Попробуйте позже или проверьте логи."
                    )
            except Exception as e:
                logger.error(f"Ошибка обновления: {e}")
                await wait_msg.edit_text(
                    "❌ <b>Ошибка при обновлении базы</b>\n\n"
                    "Технические проблемы. Попробуйте позже."
                )

        @dp.message()
        async def echo(message: types.Message):
            await message.answer(
                "ℹ️ <b>Используйте команды:</b>\n"
                "/start - начать работу\n"
                "/docs - последние документы\n" 
                "/update - обновить базу\n"
                "/help - справка\n"
                "/stats - статистика"
            )

        logger.info("🚀 Бот запускается с WebParser...")
        await dp.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())