# performance_optimizations.py
import asyncio
import functools
import concurrent.futures
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Пул потоков для блокирующих операций с файлами и парсинга
io_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=5, 
    thread_name_prefix="bot_io"
)

def run_in_thread(func):
    """Декоратор для выполнения синхронных функций в отдельном потоке"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            io_executor, 
            functools.partial(func, *args, **kwargs)
        )
    return wrapper

# Асинхронные обертки для функций database.py
@run_in_thread
def async_get_documents(organization: str = None):
    """Асинхронная версия get_documents"""
    from database import get_documents
    return get_documents(organization)

@run_in_thread
def async_get_document_count():
    """Асинхронная версия get_document_count"""
    from database import get_document_count
    return get_document_count()

@run_in_thread
def async_search_documents(query: str, limit: int = 10):
    """Асинхронная версия search_documents"""
    from database import search_documents
    return search_documents(query, limit)

@run_in_thread
def async_get_latest_documents(organization: str = None, limit: int = 5):
    """Асинхронная версия get_latest_documents"""
    from database import get_latest_documents
    return get_latest_documents(organization, limit)

@run_in_thread
def async_get_last_update_date():
    """Асинхронная версия get_last_update_date"""
    from database import get_last_update_date
    return get_last_update_date()

@run_in_thread
def async_check_database_integrity():
    """Асинхронная версия check_database_integrity"""
    from database import check_database_integrity
    return check_database_integrity()

# Обертки для парсера
@run_in_thread
def async_get_new_documents_smart(parser_instance):
    """Асинхронная версия get_new_documents_smart"""
    return parser_instance.get_new_documents_smart()

@run_in_thread
def async_get_new_documents_quick(parser_instance):
    """Асинхронная версия get_new_documents_quick"""
    return parser_instance.get_new_documents_quick()

@run_in_thread
def async_get_new_documents_full(parser_instance):
    """Асинхронная версия get_new_documents_full"""
    return parser_instance.get_new_documents_full()

@run_in_thread
def async_get_new_documents_with_boundary(parser_instance, source_key: str):
    """Асинхронная версия get_new_documents_with_boundary"""
    return parser_instance.get_new_documents_with_boundary(source_key)

async def shutdown_executor():
    """Корректное завершение пула потоков"""
    logger.info("🛑 Завершение пула потоков performance_optimizations...")
    io_executor.shutdown(wait=True)
    logger.info("✅ Пул потоков завершен")