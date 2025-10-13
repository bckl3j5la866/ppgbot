import json
import os
import logging
from typing import List, Dict, Any
from datetime import datetime
from config import DATA_DIR, NOTIFIED_FILE

logger = logging.getLogger(__name__)

BOUNDARY_FILE = os.path.join(DATA_DIR, "boundary.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_notified() -> Dict[str, List[str]]:
    _ensure_dir()
    if not os.path.exists(NOTIFIED_FILE):
        return {"federal": [], "regional": [], "rosobrnadzor": []}
    try:
        with open(NOTIFIED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for key in ["federal", "regional", "rosobrnadzor"]:
                if key not in data:
                    data[key] = []
            return data
    except Exception as e:
        logger.error(f"Ошибка чтения {NOTIFIED_FILE}: {e}")
        return {"federal": [], "regional": [], "rosobrnadzor": []}

def save_notified(data: Dict[str, List[str]]):
    _ensure_dir()
    try:
        with open(NOTIFIED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {NOTIFIED_FILE}: {e}")

def mark_as_notified(source: str, documents: List[Dict[str, Any]]):
    if not documents:
        return
    notified = load_notified()
    for doc in documents:
        url = doc.get('url')
        if url and url not in notified[source]:
            notified[source].append(url)
    if len(notified[source]) > 1000:
        notified[source] = notified[source][-1000:]
    save_notified(notified)
    logger.info(f"✅ Добавлено {len(documents)} URL в уведомленные для {source}")

def load_boundary() -> Dict[str, str]:
    _ensure_dir()
    if not os.path.exists(BOUNDARY_FILE):
        return {"federal": "", "regional": "", "rosobrnadzor": ""}
    try:
        with open(BOUNDARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка чтения {BOUNDARY_FILE}: {e}")
        return {"federal": "", "regional": "", "rosobrnadzor": ""}

def save_boundary(data: Dict[str, str]):
    _ensure_dir()
    try:
        with open(BOUNDARY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка записи {BOUNDARY_FILE}: {e}")

def get_boundary_date(source: str) -> datetime:
    data = load_boundary()
    date_str = data.get(source, "")
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return datetime.min

def update_boundary(source: str, new_docs: List[Dict[str, Any]]):
    if not new_docs:
        return
    latest_date = max(
        (datetime.strptime(d["publishDate"], "%d.%m.%Y") for d in new_docs if d.get("publishDate")),
        default=datetime.min
    )
    data = load_boundary()
    data[source] = latest_date.isoformat()
    save_boundary(data)
    logger.info(f"🧭 Обновлена граница для {source}: {latest_date}")

def filter_by_boundary(source: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    boundary_date = get_boundary_date(source)
    new_docs = []
    for doc in documents:
        try:
            doc_date = datetime.strptime(doc["publishDate"], "%d.%m.%Y")
            if doc_date > boundary_date:
                new_docs.append(doc)
        except Exception:
            continue
    logger.info(f"📄 Для {source}: {len(new_docs)} новых после {boundary_date.date()}")
    return new_docs

def should_initialize_boundary(source: str) -> bool:
    """Функция совместимости — границы теперь управляются автоматически"""
    return False
