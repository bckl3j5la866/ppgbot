import os
from dotenv import load_dotenv

load_dotenv()

# ==============================
# ⚙️ ОСНОВНЫЕ НАСТРОЙКИ БОТА
# ==============================

# 🔑 Токен Telegram-бота (загружается из .env)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Папка для хранения данных
DATA_DIR = os.getenv("DATA_DIR", "./data")

# Файлы для хранения данных
DOCUMENTS_DB_FILE = os.path.join(DATA_DIR, "documents_database.json")  # Основная база
SIMPLE_DB_FILE = os.path.join(DATA_DIR, "documents.json")              # Старая структура (для совместимости)

# Для обратной совместимости - используем основную базу
DATABASE_FILE = DOCUMENTS_DB_FILE
USERS_FILE = os.path.join(DATA_DIR, "users.json")
NOTIFIED_FILE = os.path.join(DATA_DIR, "notified.json")

# Интервал проверки обновлений (в секундах)
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "3600"))  # 1 час

# Количество документов, которые бот загружает за один раз
DOCUMENT_LIMIT = 500

# ===================================
# 📚 URL источников публикаций актов
# ===================================

# Минпросвещения Российской Федерации
FEDERAL_URL = "https://publication.pravo.gov.ru/documents/block/foiv262"

# Минобрнауки Республики Саха (Якутия)
REGIONAL_URL = (
    "https://publication.pravo.gov.ru/search/region14/iogv"
    "?pageSize=30&index=1&SignatoryAuthorityId=39ec279e-970f-43c0-85b7-4aba57163bb7"
    "&PublishDateSearchType=0&NumberSearchType=0&DocumentDateSearchType=0"
    "&JdRegSearchType=0&SortedBy=6&SortDestination=1"
)

# Рособрнадзор
OBRNADZOR_URL = "http://publication.pravo.gov.ru/documents/block/foiv320"

# ===================================
# 🌐 Заголовки HTTP-запросов
# ===================================

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
}