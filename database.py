# Добавьте в database.py
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DOCUMENTS_DB_FILE = 'data/documents.json'

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