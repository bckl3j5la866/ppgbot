import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import logging
from config import DOCUMENTS_DB_FILE as DB_FILE

logger = logging.getLogger(__name__)

# Список стоп-слов для фильтрации поиска
STOP_WORDS = {
    'приказ', 'распоряжение', 'постановление', 'закон', 'проект',
    'от', '№', 'г', 'года', 'лет', 'федеральный', 'федеральной',
    'службы', 'по', 'надзору', 'в', 'сфере', 'области', 'с',
    'образования', 'и', 'науки', 'российской', 'федерации',
    'министерства', 'просвещения', 'республики', 'саха', 'якутия',
    'об', 'утверждении', 'внесении', 'изменений', 'некоторых',
    'отдельных', 'зарегистрирован', 'зарегистрированно'
}

def init_database():
    """Инициализация базы данных, если не существует"""
    os.makedirs('data', exist_ok=True)
    if not os.path.exists(DB_FILE):
        initial_data = {
            "documents": [],
            "last_update": "",
            "created_at": datetime.now().isoformat()
        }
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Создана новая база данных: {DB_FILE}")

def get_documents(organization: str = None) -> List[Dict[str, Any]]:
    """Получает документы из базы, с фильтром по организации или без"""
    init_database()
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            documents = data.get('documents', [])
    except (FileNotFoundError, json.JSONDecodeError):
        documents = []

    if organization:
        return [doc for doc in documents if doc.get('organization') == organization]
    return documents

def get_document_count() -> int:
    """Возвращает общее количество документов в базе"""
    return len(get_documents())

def add_documents(new_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Добавляет новые документы в базу, возвращает только действительно новые"""
    init_database()
    
    # Загружаем существующие данные
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing_documents = data.get('documents', [])
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            "documents": [],
            "last_update": "",
            "created_at": datetime.now().isoformat()
        }
        existing_documents = []

    # Обеспечиваем правильную структуру новых документов
    cleaned_new_docs = []
    for doc in new_documents:
        # Если новый документ имеет структуру всей базы, извлекаем массив documents
        if isinstance(doc, dict) and 'documents' in doc:
            cleaned_new_docs.extend(doc.get('documents', []))
        # Если это массив документов, добавляем как есть
        elif isinstance(doc, list):
            cleaned_new_docs.extend(doc)
        # Если это отдельный документ, добавляем его
        elif isinstance(doc, dict) and 'url' in doc:
            cleaned_new_docs.append(doc)
    
    # Фильтруем по URL
    existing_urls = {doc['url'] for doc in existing_documents}
    truly_new_docs = [doc for doc in cleaned_new_docs if doc['url'] not in existing_urls]

    if truly_new_docs:
        logger.info(f"📥 Добавление {len(truly_new_docs)} новых документов в базу")
        
        # Обновляем структуру - добавляем только новые
        data['documents'] = existing_documents + truly_new_docs
        data['last_update'] = datetime.now().isoformat()
        
        if not data.get('created_at'):
            data['created_at'] = datetime.now().isoformat()
        
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ База обновлена. Теперь {len(data['documents'])} документов")
    else:
        logger.info("✅ Новых документов для добавления не найдено")

    return truly_new_docs

def get_latest_documents(organization: str = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Получает последние документы (сортировка по дате публикации)"""
    documents = get_documents(organization)
    # Сортируем по дате публикации (убывание)
    documents.sort(key=lambda x: x.get('publishDate', ''), reverse=True)
    return documents[:limit]

def search_documents(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Поиск документов по запросу в названии и организации с фильтрацией стоп-слов"""
    documents = get_documents()
    query_lower = query.lower()
    
    # Разбиваем запрос на слова и фильтруем стоп-слова
    query_words = [word for word in query_lower.split() 
                  if word not in STOP_WORDS and len(word) > 2]
    
    # Если остались только стоп-слова, возвращаем пустой результат
    if not query_words:
        return []
    
    results = []
    for doc in documents:
        title = doc.get('documentTitle', '').lower()
        organization = doc.get('organization', '').lower()
        
        # Ищем все оставшиеся слова (логическое И)
        if all(word in title or word in organization for word in query_words):
            results.append(doc)
    
    # Сортируем по дате публикации (новые сначала)
    results.sort(key=lambda x: x.get('publishDate', ''), reverse=True)
    
    return results[:limit]

def get_last_update_date() -> Optional[datetime]:
    """Получает дату последнего обновления базы"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_update_str = data.get('last_update')
            if last_update_str:
                return datetime.fromisoformat(last_update_str)
    except (FileNotFoundError, KeyError, ValueError):
        pass
    return None

def set_last_update_date(date: datetime) -> None:
    """Сохраняет дату последнего обновления базы"""
    init_database()
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {
            "documents": [],
            "last_update": "",
            "created_at": datetime.now().isoformat()
        }
    
    data['last_update'] = date.isoformat()
    
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_database_integrity() -> Dict[str, Any]:
    """Проверяет целостность базы данных и возвращает статистику"""
    init_database()
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"error": f"Ошибка загрузки базы: {e}"}
    
    documents = data.get('documents', [])
    
    # Проверяем на дубликаты по URL
    urls = [doc.get('url') for doc in documents if doc.get('url')]
    unique_urls = set(urls)
    duplicates = len(urls) - len(unique_urls)
    
    # Проверяем обязательные поля
    valid_docs = 0
    missing_fields = []
    
    for doc in documents:
        if all(key in doc for key in ['organization', 'documentTitle', 'url', 'publishDate']):
            valid_docs += 1
        else:
            missing_fields.append(doc.get('url', 'unknown'))
    
    return {
        "total_documents": len(documents),
        "unique_urls": len(unique_urls),
        "duplicate_documents": duplicates,
        "valid_documents": valid_docs,
        "documents_with_missing_fields": len(documents) - valid_docs,
        "last_update": data.get('last_update'),
        "created_at": data.get('created_at')
    }