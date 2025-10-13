import json
import os
import logging
from typing import Set
from config import DATA_DIR, USERS_FILE

logger = logging.getLogger(__name__)

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_users() -> Set[str]:
    """Загружает список пользователей из файла"""
    _ensure_dir()
    if not os.path.exists(USERS_FILE):
        return set()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        logger.error(f"Ошибка чтения {USERS_FILE}: {e}")
        return set()

def save_users(users: Set[str]):
    """Сохраняет список пользователей в файл"""
    _ensure_dir()
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {USERS_FILE}: {e}")

def add_user(user_id: int):
    """Добавляет пользователя в список подписчиков"""
    users = load_users()
    user_str = str(user_id)
    if user_str not in users:
        users.add(user_str)
        save_users(users)

def remove_user(user_id: int):
    """Удаляет пользователя из списка подписчиков"""
    users = load_users()
    user_str = str(user_id)
    if user_str in users:
        users.discard(user_str)
        save_users(users)