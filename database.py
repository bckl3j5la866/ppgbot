# database.py
import json
import os
import logging
from typing import Set

logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных"""
    os.makedirs('data', exist_ok=True)

def load_users() -> Set[str]:
    """Загружает список пользователей из файла"""
    init_database()
    if not os.path.exists('data/users.json'):
        return set()
    try:
        with open('data/users.json', 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception as e:
        logger.error(f"Ошибка загрузки users: {e}")
        return set()

def save_users(users: Set[str]):
    """Сохраняет список пользователей в файл"""
    init_database()
    try:
        with open('data/users.json', 'w', encoding='utf-8') as f:
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