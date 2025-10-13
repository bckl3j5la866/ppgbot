import logging
from parsers.open_data_parser import OpenDataParser
from database import get_document_count, get_documents

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def initialize_database():
    """Первоначальное заполнение единой базы данных"""
    parser = OpenDataParser(limit=500)
    
    print("🚀 Начало заполнения единой базы данных...")
    
    # Полное обновление для первоначального заполнения
    documents = parser.get_new_documents_full()
    
    print(f"✅ Единая база данных инициализирована")
    print(f"📊 Загружено документов: {get_document_count()}")
    
    # Детальная статистика
    federal_count = len(get_documents("Министерство просвещения Российской Федерации"))
    regional_count = len(get_documents("Министерство образования и науки Республики Саха (Якутия)"))
    rosobrnadzor_count = len(get_documents("Федеральная служба по надзору в сфере образования и науки"))
    
    print(f"📋 Минпросвещения РФ: {federal_count} документов")
    print(f"📋 Минобрнауки Якутии: {regional_count} документов")
    print(f"📋 Рособрнадзор: {rosobrnadzor_count} документов")
    
    return documents

if __name__ == "__main__":
    initialize_database()