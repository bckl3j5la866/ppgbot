# parsers/web_parser.py
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from pathlib import Path
from typing import List, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class WebParser:
    """Парсер для сбора документов через веб-интерфейс"""
    
    BASE_URL = "http://publication.pravo.gov.ru"
    
    # Прямые ссылки на страницы ведомств (избегаем API)
    SOURCE_URLS = {
        "federal": "http://publication.pravo.gov.ru/Department/View/262?sort=PublicationDate_desc&page=1",
        "regional": "http://publication.pravo.gov.ru/Department/View/39ec279e-970f-43c0-85b7-4aba57163bb7?sort=PublicationDate_desc&page=1",
        "rosobrnadzor": "http://publication.pravo.gov.ru/Department/View/320?sort=PublicationDate_desc&page=1"
    }
    
    ORGANIZATION_NAMES = {
        "federal": "Министерство просвещения Российской Федерации",
        "regional": "Министерство образования и науки Республики Саха (Якутия)",
        "rosobrnadzor": "Федеральная служба по надзору в сфере образования и науки"
    }

    def __init__(self, limit: int = 50):
        self.limit = limit
        self.session = self._create_session()

    def _create_session(self):
        """Создает сессию с повторными попытками"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        return session

    def get_documents(self) -> List[Dict[str, Any]]:
        """Получает документы со всех источников"""
        all_documents = []
        
        for source_key, url in self.SOURCE_URLS.items():
            try:
                logger.info(f"🔄 Парсим источник: {source_key}")
                docs = self.parse_department(url, source_key)
                all_documents.extend(docs)
                logger.info(f"✅ Получено {len(docs)} документов из {source_key}")
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга {source_key}: {e}")
        
        return all_documents

    def parse_department(self, start_url: str, source_key: str) -> List[Dict[str, Any]]:
        """Парсит документы ведомства с пагинацией"""
        org_name = self.ORGANIZATION_NAMES[source_key]
        all_docs = []
        current_url = start_url
        page_count = 0
        max_pages = 10  # Ограничиваем количество страниц
        
        logger.info(f"🌐 Начинаем парсинг для {org_name}")
        
        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"📄 Страница {page_count}: {current_url}")
            
            try:
                response = self.session.get(current_url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Парсим документы с текущей страницы
                page_docs = self.parse_page(soup, org_name)
                all_docs.extend(page_docs)
                
                logger.info(f"📑 На странице {page_count} найдено {len(page_docs)} документов")
                
                # Проверяем лимит
                if len(all_docs) >= self.limit:
                    all_docs = all_docs[:self.limit]
                    logger.info(f"⚡ Достигнут лимит в {self.limit} документов")
                    break
                
                # Ищем следующую страницу
                next_url = self.find_next_page(soup, current_url)
                if not next_url:
                    logger.info(f"🛑 Пагинация завершена на странице {page_count}")
                    break
                    
                current_url = next_url
                
            except Exception as e:
                logger.error(f"❌ Ошибка при парсинге страницы {current_url}: {e}")
                break
        
        logger.info(f"✅ Всего для {org_name}: {len(all_docs)} документов")
        return all_docs

    def parse_page(self, soup: BeautifulSoup, org_name: str) -> List[Dict[str, Any]]:
        """Парсит документы с одной страницы"""
        documents = []
        
        # Ищем контейнер с документами
        doc_containers = soup.find_all('div', class_=['document-item', 'doc-item'])
        
        if not doc_containers:
            # Альтернативный поиск - все ссылки на документы
            doc_links = soup.find_all('a', href=lambda x: x and '/Document/View/' in x)
            for link in doc_links:
                doc = self.extract_document_from_link(link, org_name)
                if doc:
                    documents.append(doc)
            return documents
        
        # Парсим из контейнеров документов
        for container in doc_containers:
            doc = self.extract_document_from_container(container, org_name)
            if doc:
                documents.append(doc)
        
        return documents

    def extract_document_from_container(self, container, org_name: str) -> Dict[str, Any]:
        """Извлекает информацию о документе из контейнера"""
        try:
            # Ищем ссылку на документ
            link = container.find('a', href=lambda x: x and '/Document/View/' in x)
            if not link:
                return None
            
            href = link.get('href')
            full_url = urljoin(self.BASE_URL, href)
            
            # Извлекаем название
            title = self.clean_text(link.get_text())
            if not title or title == "Без названия":
                title = link.get('title', 'Без названия')
            
            # Ищем дату в контейнере
            date = self.find_date_in_container(container)
            
            return {
                "organization": org_name,
                "documentTitle": title[:500],  # Ограничиваем длину
                "url": full_url,
                "publishDate": date
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения документа: {e}")
            return None

    def extract_document_from_link(self, link, org_name: str) -> Dict[str, Any]:
        """Извлекает документ из одиночной ссылки"""
        try:
            href = link.get('href')
            full_url = urljoin(self.BASE_URL, href)
            
            title = self.clean_text(link.get_text())
            if not title or title == "Без названия":
                title = link.get('title', 'Без названия')
            
            # Пытаемся найти дату в соседних элементах
            date = self.find_nearby_date(link)
            
            return {
                "organization": org_name,
                "documentTitle": title[:500],
                "url": full_url,
                "publishDate": date
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения из ссылки: {e}")
            return None

    def find_date_in_container(self, container) -> str:
        """Ищет дату в контейнере документа"""
        # Ищем по классам, которые могут содержать дату
        date_selectors = [
            '.document-date', '.doc-date', '.date', 
            '.publication-date', '.publish-date'
        ]
        
        for selector in date_selectors:
            date_elem = container.select_one(selector)
            if date_elem:
                date_text = self.clean_text(date_elem.get_text())
                date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', date_text)
                if date_match:
                    return date_match.group()
        
        # Ищем по тексту в контейнере
        container_text = container.get_text()
        date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', container_text)
        if date_match:
            return date_match.group()
        
        return "Дата не указана"

    def find_nearby_date(self, element) -> str:
        """Ищет дату в соседних элементах"""
        # Проверяем предыдущие и следующие элементы
        for sibling in [element.previous_sibling, element.next_sibling]:
            if sibling and hasattr(sibling, 'get_text'):
                text = sibling.get_text()
                date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                if date_match:
                    return date_match.group()
        
        # Проверяем родительский элемент
        parent = element.parent
        for _ in range(3):  # Проверяем до 3 уровней вверх
            if parent:
                text = parent.get_text()
                date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                if date_match:
                    return date_match.group()
                parent = parent.parent
        
        return "Дата не указана"

    def find_next_page(self, soup: BeautifulSoup, current_url: str) -> str:
        """Находит ссылку на следующую страницу"""
        # Ищем пагинацию
        pagination = soup.find('ul', class_=['pagination', 'pager'])
        if pagination:
            next_links = pagination.find_all('a', text=lambda x: x and '>' in x)
            if not next_links:
                next_links = pagination.find_all('a', text=lambda x: x and 'след' in x.lower())
            
            for link in next_links:
                href = link.get('href')
                if href:
                    return urljoin(self.BASE_URL, href)
        
        # Альтернативный поиск по классам
        next_btn = soup.find('a', class_=['next', 'page-next'])
        if next_btn and next_btn.get('href'):
            return urljoin(self.BASE_URL, next_btn.get('href'))
        
        return None

    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних пробелов"""
        if not text:
            return ""
        return ' '.join(text.split()).strip()

# Функция для обратной совместимости
def get_parser():
    """Возвращает экземпляр парсера для использования в main.py"""
    return WebParser(limit=30)