import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from pathlib import Path
from typing import List, Dict, Any
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import io
import re
from datetime import datetime
from database import add_documents, get_documents, get_last_update_date, set_last_update_date

logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> datetime:
    """Парсит дату в формате DD.MM.YYYY"""
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except (ValueError, TypeError):
        return datetime.min

class OpenDataParser:
    # URL для разных периодов (только доступные)
    CSV_URLS = {
        30: "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-30/data-legalacts-30.csv",
        90: "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-90/data-legalacts-90.csv", 
        360: "http://publication.pravo.gov.ru/opendata/7710349494-legalacts-360/data-legalacts-360.csv"
    }
    
    BASE_URL = "http://publication.pravo.gov.ru"
    
    TARGET_ORGS = {
        "a86f12ae-1908-4059-86a5-0803ea08f5ec": "Министерство просвещения Российской Федерации",
        "39ec279e-970f-43c0-85b7-4aba57163bb7": "Министерство образования и науки Республики Саха (Якутия)",
        "6fcb828d-55bf-4e1f-bb57-f9ce6cfefc0d": "Федеральная служба по надзору в сфере образования и науки"
    }

    def __init__(self, limit: int = 500, days: int = 30):
        self.limit = limit
        self.days = days
        self.csv_url = self.CSV_URLS.get(days, self.CSV_URLS[30])
        Path("data").mkdir(exist_ok=True)

    def fetch_csv(self) -> pd.DataFrame:
        """Загружает CSV файл с данными за указанный период"""
        logger.info(f"📥 Загрузка CSV с данными за {self.days} дней...")
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=5, status_forcelist=[500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))
        
        try:
            response = session.get(self.csv_url, timeout=60)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text), sep=';', encoding='utf-8')
            logger.info(f"✅ CSV за {self.days} дней загружен ({len(df)} строк)")
            return df
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки CSV за {self.days} дней: {e}")
            return pd.DataFrame()

    def get_department_links(self) -> Dict[str, str]:
        """Получает ссылки на документы целевых организаций"""
        df = self.fetch_csv()
        if df.empty:
            return {}

        df.columns = [col.strip() for col in df.columns]
        
        links = {}
        for org_id, org_name in self.TARGET_ORGS.items():
            org_row = df[df['ID принявшего органа'] == org_id]
            
            if not org_row.empty:
                link = org_row.iloc[0]['Ссылка на список документов']
                if pd.notna(link):
                    clean_link = str(link).strip()
                    full_url = urljoin(self.BASE_URL, clean_link)
                    links[org_name] = full_url
                    logger.info(f"✅ Ссылка для {org_name}")
        
        return links

    def clean_url_from_anchor(self, url: str) -> str:
        """Удаляет якорь из URL и корректирует параметры"""
        # Удаляем якорь
        clean_url = url.split('#')[0]
        
        # Парсим URL для извлечения параметров
        parsed = urlparse(clean_url)
        query_params = parse_qs(parsed.query)
        
        # Если есть якорь с index, добавляем его как параметр
        if '#' in url:
            anchor_part = url.split('#')[-1]
            if 'index=' in anchor_part:
                index_match = re.search(r'index=(\d+)', anchor_part)
                if index_match:
                    query_params['index'] = [index_match.group(1)]
        
        # Собираем URL обратно
        new_query = urlencode(query_params, doseq=True)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
        
        return clean_url

    def get_next_page_url(self, current_url: str, soup: BeautifulSoup) -> str:
        """Ищет ссылку на следующую страницу в пагинации"""
        # Ищем пагинацию по классу page-navigation
        pagination = soup.find(class_='page-navigation')
        
        if not pagination:
            logger.warning("❌ Пагинация не найдена на странице")
            return None

        # Ищем ссылку с title "Следующая"
        next_link = pagination.find('a', attrs={'title': 'Следующая'})
        
        if not next_link:
            # Ищем по иконке стрелки вправо
            next_icon = pagination.find('i', class_='fas fa-caret-right')
            if next_icon:
                next_link = next_icon.find_parent('a')

        if next_link and next_link.get('href'):
            href = next_link.get('href')
            logger.info(f"🔗 Найдена следующая страница, href: {href}")
            
            # Используем href вместо onclick
            full_url = urljoin(self.BASE_URL, href)
            
            # Очищаем URL от якоря и корректируем параметры
            clean_url = self.clean_url_from_anchor(full_url)
            logger.info(f"✅ Очищенный URL следующей страницы: {clean_url}")
            
            return clean_url

        logger.warning("❌ Ссылка на следующую страницу не найдена")
        return None

    def parse_department_documents_with_pagination(self, url: str, org_name: str) -> List[Dict[str, Any]]:
        """Парсит документы со всех страниц ведомства с поддержкой пагинации"""
        logger.info(f"🌐 Парсинг с пагинацией для {org_name}")
        
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))

        all_docs = []
        seen_urls = set()
        current_url = url
        page_count = 0
        max_pages = 20
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"📄 Страница {page_count}: {current_url}")
            
            try:
                response = session.get(current_url, timeout=30, headers=headers)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {current_url}: {e}")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Парсим документы с текущей страницы
            page_docs = self.parse_single_page(soup, org_name, seen_urls)
            
            # Добавляем в начало, так как пагинация идет от новых к старым
            all_docs = page_docs + all_docs
            
            logger.info(f"📑 На странице {page_count}: {len(page_docs)} документов")
            
            # Проверяем лимит
            if self.limit and len(all_docs) >= self.limit:
                all_docs = all_docs[:self.limit]
                logger.info(f"⚡ Достигнут лимит в {self.limit} документов")
                break
            
            # Получаем следующую страницу
            next_url = self.get_next_page_url(current_url, soup)
            if not next_url:
                logger.info(f"🛑 Пагинация завершена на странице {page_count}")
                break
            
            # Проверяем, не зациклились ли мы
            if next_url == current_url:
                logger.info(f"🛑 Обнаружен цикл, пагинация завершена")
                break
                
            current_url = next_url

        # Сортируем по дате (от новых к старым)
        all_docs.sort(key=lambda x: parse_date(x.get('publishDate', '01.01.1970')), reverse=True)
        
        logger.info(f"✅ Всего для {org_name}: {len(all_docs)} документов с {page_count} страниц")
        return all_docs

    def parse_single_page(self, soup: BeautifulSoup, org_name: str, seen_urls: set) -> List[Dict[str, Any]]:
        """Парсит документы с одной страницы"""
        docs = []

        # Ищем все ссылки на документы
        all_links = soup.find_all('a', href=True)
        document_links = [link for link in all_links if '/document/' in link['href']]

        for link in document_links:
            href = link['href']
            full_url = urljoin(self.BASE_URL, href)
            
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            # Извлекаем название и дату
            title = self.extract_document_title(link, soup)
            date = self.extract_document_date(link)

            doc = {
                "organization": org_name,
                "documentTitle": title,
                "publishDate": date,
                "url": full_url
            }
            
            docs.append(doc)

        return docs

    def extract_document_title(self, link, soup) -> str:
        """Извлекает название документа"""
        title = link.get_text(strip=True)
        
        if title and title != "Без названия":
            return title
        
        title_attr = link.get('title', '').strip()
        if title_attr:
            return title_attr
        
        # Поиск в родительских элементах
        parent = link.parent
        for _ in range(3):
            if parent:
                parent_text = parent.get_text(strip=True)
                if parent_text and len(parent_text) > 10:
                    return parent_text
                parent = parent.parent
        
        doc_id = link['href'].split('/')[-1] if '/' in link['href'] else link['href']
        return f"Документ {doc_id}"

    def extract_document_date(self, link) -> str:
        """Извлекает дату документа"""
        date = "Без даты"
        
        # Ищем дату в соседних элементах
        current_elem = link.parent
        for _ in range(5):
            if current_elem:
                text = current_elem.get_text()
                date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                if date_match:
                    return date_match.group()
                current_elem = current_elem.parent
        
        return date

    def get_new_documents_with_boundary(self, source_key: str) -> List[Dict[str, Any]]:
        """
        Получает документы для конкретного источника.
        Фильтрация теперь делается в notifier.py
        """
        dept_links = self.get_department_links()
        org_name = self.get_organization_name_by_key(source_key)
        
        if not org_name or org_name not in dept_links:
            return []
        
        url = dept_links[org_name]
        
        # Просто возвращаем все документы
        all_docs = self.parse_department_documents_with_pagination(url, org_name)
        return all_docs

    def get_organization_name_by_key(self, source_key: str) -> str:
        """Возвращает название организации по ключу"""
        mapping = {
            "federal": "Министерство просвещения Российской Федерации",
            "regional": "Министерство образования и науки Республики Саха (Якутия)", 
            "rosobrnadzor": "Федеральная служба по надзору в сфере образования и науки"
        }
        return mapping.get(source_key)

    # Методы для обратной совместимости
    def get_new_documents_smart(self) -> List[Dict[str, Any]]:
        """Умное получение новых документов"""
        logger.info("🧠 Умное обновление базы данных...")
        
        last_update = get_last_update_date()
        if last_update:
            days_since_update = (datetime.now() - last_update).days
            if days_since_update <= 7:
                self.days = 30
                self.csv_url = self.CSV_URLS[30]
                logger.info("🔍 Используем период 30 дней (быстрое обновление)")
            else:
                self.days = 90
                self.csv_url = self.CSV_URLS[90]
                logger.info("🔍 Используем период 90 дней (расширенное обновление)")
        else:
            self.days = 30
            self.csv_url = self.CSV_URLS[30]
            logger.info("🔍 Первый запуск, используем период 30 дней")
        
        dept_links = self.get_department_links()
        if not dept_links:
            return []

        all_docs = []
        for org_name, url in dept_links.items():
            docs = self.parse_department_documents_with_pagination(url, org_name)
            all_docs.extend(docs)

        new_docs = add_documents(all_docs)
        set_last_update_date(datetime.now())
        
        logger.info(f"📂 Новых документов добавлено: {len(new_docs)}")
        return new_docs

    def get_new_documents_quick(self) -> List[Dict[str, Any]]:
        """Быстрое обновление - только последние 30 дней"""
        logger.info("⚡ Быстрое обновление (30 дней)")
        self.days = 30
        self.csv_url = self.CSV_URLS[30]
        
        dept_links = self.get_department_links()
        if not dept_links:
            return []

        all_docs = []
        for org_name, url in dept_links.items():
            docs = self.parse_department_documents_with_pagination(url, org_name)
            all_docs.extend(docs)

        new_docs = add_documents(all_docs)
        set_last_update_date(datetime.now())
        
        logger.info(f"📂 Новых документов добавлено: {len(new_docs)}")
        return new_docs

    def get_new_documents_full(self) -> List[Dict[str, Any]]:
        """Полное обновление - 360 дней (для первоначального заполнения)"""
        logger.info("🔧 Полное обновление (360 дней)")
        self.days = 360
        self.csv_url = self.CSV_URLS[360]
        
        dept_links = self.get_department_links()
        if not dept_links:
            return []

        all_docs = []
        for org_name, url in dept_links.items():
            docs = self.parse_department_documents_with_pagination(url, org_name)
            all_docs.extend(docs)

        new_docs = add_documents(all_docs)
        set_last_update_date(datetime.now())
        
        logger.info(f"📂 Новых документов добавлено: {len(new_docs)}")
        return new_docs

    def get_new_documents(self) -> List[Dict[str, Any]]:
        """Совместимость со старым кодом - использует умное обновление"""
        return self.get_new_documents_smart()