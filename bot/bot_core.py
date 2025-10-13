# Версия bot_core.py с исправленной логикой показа самых новых документов

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

from config import BOT_TOKEN, DOCUMENT_LIMIT
from parsers.open_data_parser import OpenDataParser

from performance_optimizations import (
    async_get_documents, async_get_document_count, async_search_documents,
    async_get_latest_documents, async_get_last_update_date, async_check_database_integrity,
    async_get_new_documents_quick, async_get_new_documents_full,
    shutdown_executor
)

from bot.users_storage import add_user, remove_user, load_users

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
parser = OpenDataParser(limit=DOCUMENT_LIMIT)


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Поиск документов"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
                KeyboardButton(text="🔄 Обновить базу")
            ],
            [
                KeyboardButton(text="ℹ️ Помощь"),
                KeyboardButton(text="🔔 Управление подпиской")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или введите команду..."
    )


def _parse_date_safe(date_str: str) -> datetime:
    """Безопасный парсинг даты из формата DD.MM.YYYY"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except (ValueError, TypeError):
        return datetime.min


async def get_newest_documents_per_organization():
    """Получает самые новые документы от каждой организации"""
    try:
        # Получаем все документы из базы
        all_documents = await async_get_documents()
        
        if not all_documents:
            return []
        
        # Группируем документы по организациям
        org_documents = {}
        for doc in all_documents:
            org = doc.get('organization', '')
            if org not in org_documents:
                org_documents[org] = []
            org_documents[org].append(doc)
        
        # Для каждой организации находим самый новый документ
        newest_docs = []
        for org, docs in org_documents.items():
            if docs:
                # Сортируем документы организации по дате (новые сначала)
                docs.sort(key=lambda x: _parse_date_safe(x.get('publishDate', '01.01.1970')), reverse=True)
                # Берем самый новый документ
                newest_docs.append(docs[0])
        
        # Сортируем все самые новые документы по дате (новые сначала)
        newest_docs.sort(key=lambda x: _parse_date_safe(x.get('publishDate', '01.01.1970')), reverse=True)
        
        return newest_docs
        
    except Exception as e:
        logger.error(f"Ошибка при получении самых новых документов: {e}")
        return []


@dp.message(Command(commands=["start", "help"]))
async def send_welcome(message: types.Message):
    users = load_users()
    user_str = str(message.from_user.id)
    is_new_user = user_str not in users

    total_count = await async_get_document_count()
    last_update = await async_get_last_update_date()

    text = (
        "👋 <b>Добро пожаловать в бот правовых актов!</b>\n\n"
        "Я отслеживаю документы трёх ведомств:\n"
        "• Минпросвещения России\n"
        "• Минобрнауки Якутии\n"
        "• Рособрнадзор\n\n"
        "📊 <b>Текущее состояние:</b>\n"
        f"• Документов в базе: {total_count}\n"
        f"• Последнее обновление: {last_update.strftime('%d.%m.%Y %H:%M') if last_update else 'никогда'}\n"
    )
    await message.answer(text)

    if is_new_user:
        # Получаем самые новые документы от каждой организации
        newest_docs = await get_newest_documents_per_organization()
        
        if newest_docs:
            await message.answer("📌 <b>Самые свежие документы по каждому ведомству:</b>")
            
            for doc in newest_docs:
                title = doc.get('documentTitle', 'Без названия')
                if len(title) > 100:
                    title = title[:100] + "..."
                text_doc = (
                    f"<b>{doc.get('organization','')}</b>\n"
                    f"📅 {doc.get('publishDate','')}\n"
                    f"<i>{title}</i>\n"
                    f"<a href='{doc.get('url','')}'>📄 Открыть документ</a>"
                )
                await message.answer(text_doc)
                await asyncio.sleep(0.2)
            
            # Показываем информацию о количестве ведомств
            orgs_count = len(set(doc.get('organization', '') for doc in newest_docs))
            await message.answer(f"📋 Показаны самые свежие документы от {orgs_count} ведомств")
        else:
            await message.answer("📭 В базе пока нет документов")

        add_user(message.from_user.id)

    await message.answer("Готов к работе. Выберите действие:", reply_markup=get_main_keyboard())


@dp.message(F.text == "🔍 Поиск документов")
async def handle_search(message: types.Message):
    await message.answer("🔍 Введите поисковый запрос (например: 'приказ образование'):")


@dp.message(F.text == "📊 Статистика")
async def handle_stats(message: types.Message):
    try:
        total_count = await async_get_document_count()
        last_update = await async_get_last_update_date()
        integrity = await async_check_database_integrity()
        
        # Получаем самые новые документы для отображения дат
        newest_docs = await get_newest_documents_per_organization()
        
        federal_count = len(await async_get_documents("Министерство просвещения Российской Федерации"))
        regional_count = len(await async_get_documents("Министерство образования и науки Республики Саха (Якутия)"))
        rosobrnadzor_count = len(await async_get_documents("Федеральная служба по надзору в сфере образования и науки"))
        
        # Находим даты самых новых документов для каждого ведомства
        federal_latest_date = "нет документов"
        regional_latest_date = "нет документов" 
        rosobrnadzor_latest_date = "нет документов"
        
        for doc in newest_docs:
            org = doc.get('organization', '')
            date = doc.get('publishDate', '')
            if "Министерство просвещения Российской Федерации" in org:
                federal_latest_date = date
            elif "Министерство образования и науки Республики Саха" in org:
                regional_latest_date = date
            elif "Федеральная служба по надзору" in org:
                rosobrnadzor_latest_date = date
        
        text = (
            "📊 <b>Статистика базы данных</b>\n\n"
            f"• Всего документов: <b>{total_count}</b>\n\n"
            f"<b>По ведомствам:</b>\n"
            f"• Минпросвещения РФ: <b>{federal_count}</b> (последний: {federal_latest_date})\n"
            f"• Минобрнауки Якутии: <b>{regional_count}</b> (последний: {regional_latest_date})\n"
            f"• Рособрнадзор: <b>{rosobrnadzor_count}</b> (последний: {rosobrnadzor_latest_date})\n\n"
            f"• Последнее обновление: {last_update.strftime('%d.%m.%Y %H:%M') if last_update else 'никогда'}\n"
            f"• База создана: {integrity.get('created_at', 'неизвестно')}"
        )
        await message.answer(text, reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer("❌ Не удалось получить статистику")


@dp.message(F.text == "🔄 Обновить базу")
async def handle_update(message: types.Message):
    await message.answer("🔄 Запуск принудительного обновления базы...")
    try:
        new_docs = await async_get_new_documents_quick(parser)
        if new_docs:
            await message.answer(f"✅ Добавлено {len(new_docs)} новых документов", reply_markup=get_main_keyboard())
            
            # Показываем новые документы
            new_docs.sort(key=lambda x: _parse_date_safe(x.get('publishDate', '01.01.1970')), reverse=True)
            
            for doc in new_docs[:3]:  # Показываем первые 3 новых документа
                title = doc.get('documentTitle', 'Без названия')
                if len(title) > 100:
                    title = title[:100] + "..."
                text = (
                    f"<b>{doc.get('organization','')}</b>\n"
                    f"📅 {doc.get('publishDate','')}\n"
                    f"<i>{title}</i>\n"
                    f"<a href='{doc.get('url','')}'>📄 Открыть документ</a>"
                )
                await message.answer(text)
                await asyncio.sleep(0.2)
                
            if len(new_docs) > 3:
                await message.answer(f"📋 И еще <b>{len(new_docs) - 3}</b> новых документов.")
        else:
            await message.answer("✅ Новых документов не найдено", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Ошибка обновления базы: {e}")
        await message.answer("❌ Ошибка при обновлении базы")


@dp.message(F.text == "ℹ️ Помощь")
async def handle_help(message: types.Message):
    text = (
        "ℹ️ <b>Справка по боту</b>\n\n"
        "📋 <b>Основные команды:</b>\n"
        "• <b>🔍 Поиск документов</b> - найти документы по ключевым словам\n"
        "• <b>📊 Статистика</b> - информация о базе данных\n"
        "• <b>🔄 Обновить базу</b> - принудительная проверка новых документов\n\n"
        "🔔 <b>Автоматические уведомления:</b>\n"
        "Бот автоматически проверяет новые документы каждый час и присылает уведомления.\n\n"
        "📚 <b>Отслеживаемые источники:</b>\n"
        "• Минпросвещения России\n"
        "• Минобрнауки Якутии\n" 
        "• Рособрнадзор"
    )
    await message.answer(text, reply_markup=get_main_keyboard())


@dp.message(F.text == "🔔 Управление подпиской")
async def handle_subscription(message: types.Message):
    users = load_users()
    user_str = str(message.from_user.id)
    
    if user_str in users:
        text = (
            "🔔 <b>Управление подпиской</b>\n\n"
            "Вы <b>подписаны</b> на уведомления о новых документах.\n\n"
            "Чтобы отписаться, отправьте команду /stop"
        )
    else:
        text = (
            "🔔 <b>Управление подпиской</b>\n\n"
            "Вы <b>не подписаны</b> на уведомления.\n\n"
            "Чтобы подписаться, отправьте команду /start"
        )
    await message.answer(text, reply_markup=get_main_keyboard())


@dp.message(Command("stop"))
async def handle_stop(message: types.Message):
    remove_user(message.from_user.id)
    await message.answer(
        "🔔 Вы отписались от уведомлений.\n"
        "Чтобы снова подписаться, отправьте /start",
        reply_markup=get_main_keyboard()
    )


# Обработчик поисковых запросов
@dp.message(F.text & ~F.text.startswith('/'))
async def handle_search_query(message: types.Message):
    query = message.text.strip()
    
    # Игнорируем текст, который совпадает с кнопками (они обрабатываются другими обработчиками)
    if query in ["🔍 Поиск документов", "📊 Статистика", 
                 "🔄 Обновить базу", "ℹ️ Помощь", "🔔 Управление подпиской"]:
        return
    
    if not query or len(query) < 2:
        await message.answer("❌ Введите поисковый запрос (минимум 2 символа)")
        return
    
    await message.answer(f"🔍 Ищу документы по запросу: <b>{query}</b>")
    
    try:
        results = await async_search_documents(query, limit=10)
        if results:
            await message.answer(f"✅ Найдено документов: <b>{len(results)}</b>")
            
            # Сортируем результаты по дате (новые сначала)
            results.sort(key=lambda x: _parse_date_safe(x.get('publishDate', '01.01.1970')), reverse=True)
            
            for doc in results[:5]:  # Показываем первые 5 результатов
                title = doc.get('documentTitle', 'Без названия')
                if len(title) > 100:
                    title = title[:100] + "..."
                text = (
                    f"<b>{doc.get('organization','')}</b>\n"
                    f"📅 {doc.get('publishDate','')}\n"
                    f"<i>{title}</i>\n"
                    f"<a href='{doc.get('url','')}'>📄 Открыть документ</a>"
                )
                await message.answer(text)
                await asyncio.sleep(0.2)
            
            if len(results) > 5:
                await message.answer(f"📋 И еще <b>{len(results) - 5}</b> документов. Уточните запрос для более точного поиска.")
        else:
            await message.answer("❌ По вашему запросу ничего не найдено. Попробуйте другие ключевые слова.")
    
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer("❌ Произошла ошибка при поиске. Попробуйте позже.")


async def main():
    logger.info("🚀 Запуск Telegram-бота (с исправленным показом самых новых документов)...")
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен пользователем.")
    finally:
        await shutdown_executor()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Приложение полностью остановлено.")