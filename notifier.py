import asyncio
import logging
from bot.bot_core import bot
from parsers.open_data_parser import OpenDataParser
from bot.users_storage import load_users
from database import add_documents
from config import CHECK_INTERVAL_SECONDS
from datetime import datetime

from performance_optimizations import (
    async_get_document_count, async_get_last_update_date,
    shutdown_executor, run_in_thread
)
from storage import mark_as_notified, filter_by_boundary, update_boundary

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def send_notifications():
    parser = OpenDataParser(limit=100)
    initial_count = await async_get_document_count()
    last_update = await async_get_last_update_date()
    logger.info(f"📊 Начальное состояние базы: {initial_count} документов")

    while True:
        try:
            logger.info("🔍 Проверка новых документов...")

            all_federal = await async_get_all_documents(parser, "federal")
            all_regional = await async_get_all_documents(parser, "regional") 
            all_rosobrnadzor = await async_get_all_documents(parser, "rosobrnadzor")

            new_federal = filter_by_boundary("federal", all_federal)
            new_regional = filter_by_boundary("regional", all_regional)
            new_rosobrnadzor = filter_by_boundary("rosobrnadzor", all_rosobrnadzor)

            all_new_docs = new_federal + new_regional + new_rosobrnadzor

            if all_new_docs:
                added_docs = add_documents(all_new_docs)

                if added_docs:
                    users = load_users()
                    logger.info(f"📨 Найдено {len(added_docs)} новых документов для {len(users)} пользователей")

                    for user_id in users:
                        try:
                            current_count = await async_get_document_count()
                            await bot.send_message(
                                user_id,
                                f"📢 <b>Обнаружены новые документы!</b>\n\n"
                                f"• Добавлено: <b>{len(added_docs)}</b> документов\n"
                                f"• Всего в базе: <b>{current_count}</b>\n"
                                f"• Время обновления: {datetime.now().strftime('%H:%M')}"
                            )
                            for doc in added_docs[:3]:
                                title = doc['documentTitle']
                                if len(title) > 100:
                                    title = title[:100] + "..."
                                text = (
                                    f"<b>{doc['organization']}</b>\n"
                                    f"📅 {doc['publishDate']}\n"
                                    f"<i>{title}</i>\n"
                                    f"<a href='{doc['url']}'>📄 Открыть документ</a>"
                                )
                                await bot.send_message(user_id, text)
                                await asyncio.sleep(0.2)
                            if len(added_docs) > 3:
                                await bot.send_message(
                                    user_id,
                                    f"📋 И еще <b>{len(added_docs) - 3}</b> документов. "
                                    f"Нажмите «📥 Последние документы» чтобы посмотреть все."
                                )
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")

                    mark_as_notified("federal", new_federal)
                    mark_as_notified("regional", new_regional)
                    mark_as_notified("rosobrnadzor", new_rosobrnadzor)

                    update_boundary("federal", new_federal)
                    update_boundary("regional", new_regional)
                    update_boundary("rosobrnadzor", new_rosobrnadzor)

                    logger.info(f"✅ Уведомления отправлены и границы обновлены")
            else:
                logger.info("✅ Новых документов не обнаружено")

            logger.info(f"⏳ Ожидание {CHECK_INTERVAL_SECONDS} секунд до следующей проверки")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"❌ Ошибка в процессе проверки: {e}")
            await asyncio.sleep(60)

@run_in_thread
def async_get_all_documents(parser_instance, source_key: str):
    dept_links = parser_instance.get_department_links()
    org_name = parser_instance.get_organization_name_by_key(source_key)
    if not org_name or org_name not in dept_links:
        return []
    url = dept_links[org_name]
    all_docs = parser_instance.parse_department_documents_with_pagination(url, org_name)
    return all_docs

async def start_notifier():
    logger.info("🚀 Запуск службы уведомлений...")
    try:
        await send_notifications()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в службе уведомлений: {e}")
        await asyncio.sleep(60)
        await start_notifier()

async def shutdown_notifier():
    logger.info("🛑 Остановка службы уведомлений...")
    await shutdown_executor()

if __name__ == "__main__":
    logger.info("🚀 Запуск автономной службы уведомлений...")
    try:
        asyncio.run(start_notifier())
    except KeyboardInterrupt:
        logger.info("🛑 Служба уведомлений остановлена пользователем")
    finally:
        asyncio.run(shutdown_notifier())
