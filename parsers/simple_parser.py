# parsers/simple_parser.py
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SimpleParser:
    def __init__(self):
        self.base_url = "http://publication.pravo.gov.ru"
        self.sources = {
            "federal": "https://publication.pravo.gov.ru/documents/block/foiv262",
            "regional": "https://publication.pravo.gov.ru/search/region14/iogv?pageSize=30&index=1&SignatoryAuthorityId=39ec279e-970f-43c0-85b7-4aba57163bb7",
            "rosobrnadzor": "http://publication.pravo.gov.ru/documents/block/foiv320"
        }

    def get_documents(self) -> List[Dict[str, Any]]:
        """Получает документы со всех источников"""
        all_documents = []
        
        for source_name, url in self.sources.items():
            try:
                docs = self.parse_source(url, source_name)
                all_documents.extend(docs)
                logger.info(f"✅ Получено {len(docs)} документов из {source_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга {source_name}: {e}")
        
        return all_documents

    def parse_source(self, url: str, source_name: str) -> List[Dict[str, Any]]:
        """Парсит документы из одного источника"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            documents = []
            
            # Простой парсинг - можно улучшить под конкретную структуру сайта
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                if '/document/' in href:
                    doc_url = urljoin(self.base_url, href)
                    title = link.get_text(strip=True) or link.get('title', 'Без названия')
                    
                    document = {
                        'organization': self.get_organization_name(source_name),
                        'documentTitle': title[:200],  # Ограничиваем длину
                        'url': doc_url,
                        'publishDate': '13.10.2025'  # Заглушка - нужно извлекать из страницы
                    }
                    documents.append(document)
            
            return documents[:10]  # Ограничиваем количество для теста
            
        except Exception as e:
            logger.error(f"Ошибка парсинга {url}: {e}")
            return []

    def get_organization_name(self, source_key: str) -> str:
        """Возвращает название организации по ключу"""
        names = {
            "federal": "Министерство просвещения Российской Федерации",
            "regional": "Министерство образования и науки Республики Саха (Якутия)",
            "rosobrnadzor": "Федеральная служба по надзору в сфере образования и науки"
        }
        return names.get(source_key, "Неизвестная организация")