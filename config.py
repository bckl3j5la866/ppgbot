import os

# ==============================
# ⚙️ ОСНОВНЫЕ НАСТРОЙКИ БОТА
# ==============================

# 🔑 Токен Telegram-бота (загружается из переменных окружения bothost.ru)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден. Убедитесь, что токен установлен в настройках bothost.ru")

# Папка для хранения данных
DATA_DIR = "./data"

# Файлы для хранения данных
DOCUMENTS_DB_FILE = os.path.join(DATA_DIR, "documents_database.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# Интервал проверки обновлений (в секундах)
CHECK_INTERVAL_SECONDS = 3600  # 1 час

# Количество документов, которые бот загружает за один раз
DOCUMENT_LIMIT = 500

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