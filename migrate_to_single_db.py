import json
import logging
import shutil
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_to_single_database():
    """Мигрирует все данные в единую базу и удаляет старый файл"""
    
    # Пути к файлам
    main_db_path = 'data/documents_database.json'
    old_db_path = 'data/documents.json'
    backup_path = f'data/documents_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    documents_from_old = []
    documents_from_main = []
    
    # Загружаем данные из основной базы
    try:
        with open(main_db_path, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
            documents_from_main = main_data.get('documents', [])
        logger.info(f"📊 Загружено {len(documents_from_main)} документов из основной базы")
    except FileNotFoundError:
        logger.warning("⚠️ Основная база не найдена, создаем новую")
        main_data = {
            "documents": [],
            "last_update": "",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки основной базы: {e}")
        return False
    
    # Загружаем данные из старой базы
    try:
        with open(old_db_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            # Старый файл может быть массивом или объектом
            if isinstance(old_data, list):
                documents_from_old = old_data
            elif isinstance(old_data, dict) and 'documents' in old_data:
                documents_from_old = old_data.get('documents', [])
            else:
                documents_from_old = []
        logger.info(f"📊 Загружено {len(documents_from_old)} документов из старой базы")
    except FileNotFoundError:
        logger.info("ℹ️ Старая база не найдена, пропускаем")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки старой базы: {e}")
        return False
    
    # Создаем бэкап старого файла
    if documents_from_old:
        try:
            shutil.copy2(old_db_path, backup_path)
            logger.info(f"📦 Создан бэкап старой базы: {backup_path}")
        except Exception as e:
            logger.error(f"⚠️ Не удалось создать бэкап: {e}")
    
    # Объединяем документы (убираем дубликаты по URL)
    all_documents = documents_from_main
    existing_urls = {doc['url'] for doc in documents_from_main}
    
    added_count = 0
    for doc in documents_from_old:
        if doc.get('url') not in existing_urls:
            all_documents.append(doc)
            existing_urls.add(doc['url'])
            added_count += 1
    
    logger.info(f"🔄 Добавлено {added_count} новых документов из старой базы")
    
    # Сохраняем объединенную базу
    main_data['documents'] = all_documents
    main_data['last_update'] = datetime.now().isoformat()
    
    if not main_data.get('created_at'):
        main_data['created_at'] = datetime.now().isoformat()
    
    try:
        with open(main_db_path, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Сохранена объединенная база: {len(all_documents)} документов")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения объединенной базы: {e}")
        return False
    
    # Удаляем старый файл (опционально)
    try:
        os.remove(old_db_path)
        logger.info("🗑️ Старый файл documents.json удален")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось удалить старый файл: {e}")
    
    return True

if __name__ == "__main__":
    logger.info("🚀 Начало миграции на единую базу данных...")
    if migrate_to_single_database():
        logger.info("✅ Миграция успешно завершена!")
    else:
        logger.error("❌ Миграция не удалась!")