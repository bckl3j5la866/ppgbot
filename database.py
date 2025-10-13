# database.py - полная версия с пользователями и документами
import json
import os
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

# Файлы базы данных
USERS_FILE = 'data/users.json'
DOCUMENTS_DB_FILE = 'data/documents.json'

# ==============================
# 📊 ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ
# ==============================

def init_database():
    """Инициализация базы данных"""
    os.makedirs('data', exist_ok=True)

def load_users() -> Set[str]:
    """Загружает список пользователей из файла"""
    init_database()
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception as e:
        logger.error(f"Ошибка загрузки users: {e}")
        return set()

def save_users(users: Set[str]):
    """Сохраняет список пользователей в файл"""
    init_database()
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(users), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения users: {e}")

def add_user(user_id: int):
    """Добавляет пользователя в список подписчиков"""
    users = load_users()
    user_str = str(user_id)
    if user_str not in users:
        users.add(user_str)
        save_users(users)
        logger.info(f"✅ Добавлен пользователь: {user_id}")

def remove_user(user_id: int):
    """Удаляет пользователя из списка подписчиков"""
    users = load_users()
    user_str = str(user_id)
    if user_str in users:
        users.discard(user_str)
        save_users(users)
        logger.info(f"❌ Удален пользователь: {user_id}")

def get_user_count() -> int:
    """Возвращает количество пользователей"""
    return len(load_users())

# ==============================
# 📄 ФУНКЦИИ ДЛЯ РАБОТЫ С ДОКУМЕНТАМИ
# ==============================

def init_documents_db():
    """Инициализация базы документов"""
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(DOCUMENTS_DB_FILE):
        with open(DOCUMENTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def save_documents(documents: List[Dict[str, Any]]):
    """Сохраняет документы в базу"""
    init_documents_db()
    try:
        with open(DOCUMENTS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения документов: {e}")

def load_documents() -> List[Dict[str, Any]]:
    """Загружает документы из базы"""
    init_documents_db()
    try:
        with open(DOCUMENTS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def add_documents(new_documents: List[Dict[str, Any]]) -> int:
    """Добавляет новые документы в базу, возвращает количество добавленных"""
    existing_docs = load_documents()
    existing_urls = {doc['url'] for doc in existing_docs}
    
    truly_new = [doc for doc in new_documents if doc['url'] not in existing_urls]
    
    if truly_new:
        all_docs = existing_docs + truly_new
        save_documents(all_docs)
        logger.info(f"✅ Добавлено {len(truly_new)} новых документов")
    
    return len(truly_new)

def get_recent_documents(limit: int = 5) -> List[Dict[str, Any]]:
    """Возвращает последние документы"""
    documents = load_documents()
    return documents[-limit:] if documents else []

def get_document_count() -> int:
    """Возвращает количество документов в базе"""
    return len(load_documents())