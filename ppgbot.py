import requests
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import json
import os
import io

# Настройки
TELEGRAM_BOT_TOKEN = ''  # ЗАМЕНИТЕ НА ВАШ ТОКЕН
BASE_URL = 'http://publication.pravo.gov.ru'

# URL для разных типов документов
FEDERAL_URL = BASE_URL + '/documents/block/foiv262'
REGIONAL_URL = BASE_URL + '/search/region14/iogv?pageSize=30&index=1&SignatoryAuthorityId=39ec279e-970f-43c0-85b7-4aba57163bb7&&PublishDateSearchType=0&NumberSearchType=0&DocumentDateSearchType=0&JdRegSearchType=0&SortedBy=6&SortDestination=1'

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DocumentBot:
    def __init__(self):
        self.seen_federal_file = 'seen_federal_documents.json'
        self.seen_regional_file = 'seen_regional_documents.json'
        self.seen_federal = self.load_seen_documents(self.seen_federal_file)
        self.seen_regional = self.load_seen_documents(self.seen_regional_file)
        self.current_state = {}  # Для отслеживания состояния пользователей

    def load_seen_documents(self, filename):
        """Загружаем историю просмотренных документов"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Ошибка загрузки истории {filename}: {e}")
            return set()

    def save_seen_documents(self, doc_type):
        """Сохраняем историю документов"""
        try:
            if doc_type == 'federal':
                filename = self.seen_federal_file
                documents = self.seen_federal
            else:
                filename = self.seen_regional_file
                documents = self.seen_regional
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(list(documents), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории {doc_type}: {e}")

    def get_seen_documents(self, doc_type):
        """Получаем множество просмотренных документов по типу"""
        return self.seen_federal if doc_type == 'federal' else self.seen_regional

    def add_seen_document(self, doc_type, doc_number):
        """Добавляем документ в просмотренные"""
        if doc_type == 'federal':
            self.seen_federal.add(doc_number)
        else:
            self.seen_regional.add(doc_number)
        self.save_seen_documents(doc_type)

    def create_main_keyboard(self):
        """Создает основную клавиатуру внизу экрана"""
        keyboard = [
            ["📋 Федеральные документы", "🏛️ Региональные документы"],
            ["❓ Помощь"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def create_federal_keyboard(self):
        """Создает клавиатуру для федеральных документов"""
        keyboard = [
            ["🔍 Проверить обновления (Фед)", "📄 Последние документы (Фед)"],
            ["🏠 Главное меню"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def create_regional_keyboard(self):
        """Создает клавиатуру для региональных документов"""
        keyboard = [
            ["🔍 Проверить обновления (Рег)", "📄 Последние документы (Рег)"],
            ["🏠 Главное меню"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def create_document_keyboard(self, document, doc_type):
        """Создает инлайн клавиатуру для документа со ссылками"""
        keyboard = [
            [InlineKeyboardButton("📄 Открыть документ", url=document['link'])],
            [InlineKeyboardButton("📎 Скачать PDF", callback_data=f"download_{doc_type}_{document['number']}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_back_keyboard(self, doc_type):
        """Создает клавиатуру для возврата"""
        type_name = "Федеральные" if doc_type == 'federal' else "Региональные"
        keyboard = [
            [f"🔍 Проверить ещё раз ({type_name})", f"📄 Все документы ({type_name})"],
            ["🏠 Главное меню"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    def get_pdf_headers(self):
        """Возвращает правильные заголовки для скачивания PDF"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def download_pdf(self, pdf_url, document_number):
        """Скачивает PDF файл и возвращает его содержимое с правильным именем"""
        try:
            headers = self.get_pdf_headers()
            response = requests.get(pdf_url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Проверяем, что это действительно PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type or response.content[:4] == b'%PDF':
                pdf_content = response.content
                return pdf_content, f"{document_number}.pdf"
            else:
                logger.error(f"Получен не PDF файл: {content_type}")
                return None, None
                
        except Exception as e:
            logger.error(f"Ошибка скачивания PDF: {e}")
            return None, None

    def parse_documents(self, doc_type):
        """Парсим документы с сайта в зависимости от типа"""
        try:
            url = FEDERAL_URL if doc_type == 'federal' else REGIONAL_URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            logger.info(f"Запрашиваю {doc_type} данные с сайта...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            documents = []
            
            # Ищем все блоки с документами
            document_blocks = soup.find_all('div', class_='documents-table-cell')
            logger.info(f"Найдено {doc_type} блоков: {len(document_blocks)}")
            
            for block in document_blocks:
                try:
                    # Извлекаем номер документа
                    number_elements = block.find_all('span', class_='info-data')
                    if not number_elements:
                        continue
                    
                    doc_number = number_elements[0].text.strip()
                    
                    # Извлекаем название документа
                    name_element = block.find('a', class_='documents-item-name')
                    if not name_element:
                        continue
                    
                    doc_name = name_element.get_text(separator=' ', strip=True)
                    
                    # Извлекаем дату опубликования
                    doc_date = number_elements[1].text.strip() if len(number_elements) > 1 else 'Не указана'
                    
                    # Формируем ссылки
                    doc_link = BASE_URL + name_element['href']
                    
                    pdf_element = block.find('a', title='Скачать PDF файл')
                    pdf_link = BASE_URL + pdf_element['href'] if pdf_element else ''
                    
                    # Получаем размер файла
                    size_element = pdf_element.find('span', class_='documents-pdf-downloadlink') if pdf_element else None
                    file_size = size_element.text.strip() if size_element else 'Неизвестно'
                    
                    # Определяем, новый ли документ
                    seen_documents = self.get_seen_documents(doc_type)
                    is_new = doc_number not in seen_documents
                    
                    documents.append({
                        'number': doc_number,
                        'name': doc_name,
                        'date': doc_date,
                        'link': doc_link,
                        'pdf': pdf_link,
                        'size': file_size,
                        'is_new': is_new,
                        'type': doc_type
                    })
                    
                except Exception as e:
                    logger.error(f"Ошибка парсинга элемента: {e}")
                    continue
            
            return documents
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении {doc_type} страницы: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге {doc_type}: {e}")
            return None

    def format_document_message(self, document, is_new=True):
        """Форматируем сообщение о документе"""
        doc_type = "федеральный" if document['type'] == 'federal' else "региональный"
        status = "🆕 НОВЫЙ ДОКУМЕНТ" if is_new else "📄 Документ"
        
        # Обрезаем длинное название для лучшего отображения
        name = document['name']
        if len(name) > 200:
            name = name[:200] + "..."
        
        message = (
            f"{status} ({doc_type})\n"
            f"📋 {name}\n"
            f"📅 Дата: {document['date']}\n"
            f"🔢 Номер: {document['number']}\n"
            f"💾 Размер: {document['size']}"
        )
            
        return message

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_text = (
            "👋 Привет! Я бот для отслеживания документов с pravo.gov.ru\n\n"
            "Выберите тип документов:"
        )
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(welcome_text, reply_markup=keyboard)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "📋 Помощь по боту:\n\n"
            "• 📋 **Федеральные документы** - приказы министерств РФ\n"
            "• 🏛️ **Региональные документы** - приказы региональных органов власти\n"
            "• 🔍 **Проверить обновления** - покажет только НОВЫЕ документы\n"
            "• 📄 **Последние документы** - покажет все документы с сайта\n"
            "• Для каждого документа доступны кнопки для просмотра и скачивания PDF\n\n"
            "Бот автоматически запоминает какие документы вы уже видели."
        )
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(help_text, reply_markup=keyboard, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений (кнопок)"""
        text = update.message.text
        user_id = update.message.from_user.id
        
        if text == "📋 Федеральные документы":
            await self.show_federal_menu(update, context)
        elif text == "🏛️ Региональные документы":
            await self.show_regional_menu(update, context)
        elif text == "❓ Помощь":
            await self.help_command(update, context)
        elif text == "🏠 Главное меню":
            await self.show_main_menu(update, context)
        elif text == "🔍 Проверить обновления (Фед)":
            await self.check_federal_updates(update, context)
        elif text == "📄 Последние документы (Фед)":
            await self.show_federal_documents(update, context)
        elif text == "🔍 Проверить обновления (Рег)":
            await self.check_regional_updates(update, context)
        elif text == "📄 Последние документы (Рег)":
            await self.show_regional_documents(update, context)
        elif text.startswith("🔍 Проверить ещё раз"):
            if "(Федеральные)" in text:
                await self.check_federal_updates(update, context)
            else:
                await self.check_regional_updates(update, context)
        elif text.startswith("📄 Все документы"):
            if "(Федеральные)" in text:
                await self.show_federal_documents(update, context)
            else:
                await self.show_regional_documents(update, context)
        else:
            await update.message.reply_text("Неизвестная команда. Используйте кнопки ниже.", reply_markup=self.create_main_keyboard())

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню"""
        welcome_text = "🏠 Главное меню\n\nВыберите тип документов:"
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(welcome_text, reply_markup=keyboard)

    async def show_federal_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню федеральных документов"""
        menu_text = "📋 Федеральные документы\n\nВыберите действие:"
        keyboard = self.create_federal_keyboard()
        await update.message.reply_text(menu_text, reply_markup=keyboard)

    async def show_regional_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню региональных документов"""
        menu_text = "🏛️ Региональные документы\n\nВыберите действие:"
        keyboard = self.create_regional_keyboard()
        await update.message.reply_text(menu_text, reply_markup=keyboard)

    async def check_federal_updates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка обновлений федеральных документов"""
        status_msg = await update.message.reply_text("🔍 Проверяю обновления федеральных документов...")
        
        documents = self.parse_documents('federal')
        
        if documents is None:
            await status_msg.edit_text("❌ Ошибка при получении данных федеральных документов")
            keyboard = self.create_back_keyboard('federal')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        if not documents:
            await status_msg.edit_text("📭 Федеральные документы не найдены")
            keyboard = self.create_back_keyboard('federal')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        new_documents = [doc for doc in documents if doc['is_new']]
        
        if not new_documents:
            await status_msg.edit_text("✅ Новых федеральных документов нет")
            keyboard = self.create_back_keyboard('federal')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        await status_msg.edit_text(f"🎉 Найдено {len(new_documents)} новых федеральных документов!")
        
        # Отправляем каждый новый документ отдельным сообщением с инлайн-кнопками
        for doc in new_documents:
            try:
                message = self.format_document_message(doc, is_new=True)
                keyboard = self.create_document_keyboard(doc, 'federal')
                await update.message.reply_text(message, reply_markup=keyboard, disable_web_page_preview=True)
                
                # Добавляем в просмотренные
                self.add_seen_document('federal', doc['number'])
                
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                continue
        
        # Отправляем клавиатуру для дальнейших действий
        keyboard = self.create_back_keyboard('federal')
        await update.message.reply_text("✅ Проверка федеральных документов завершена!\n\nВыберите следующее действие:", reply_markup=keyboard)

    async def check_regional_updates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка обновлений региональных документов"""
        status_msg = await update.message.reply_text("🔍 Проверяю обновления региональных документов...")
        
        documents = self.parse_documents('regional')
        
        if documents is None:
            await status_msg.edit_text("❌ Ошибка при получении данных региональных документов")
            keyboard = self.create_back_keyboard('regional')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        if not documents:
            await status_msg.edit_text("📭 Региональные документы не найдены")
            keyboard = self.create_back_keyboard('regional')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        new_documents = [doc for doc in documents if doc['is_new']]
        
        if not new_documents:
            await status_msg.edit_text("✅ Новых региональных документов нет")
            keyboard = self.create_back_keyboard('regional')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        await status_msg.edit_text(f"🎉 Найдено {len(new_documents)} новых региональных документов!")
        
        # Отправляем каждый новый документ отдельным сообщением с инлайн-кнопками
        for doc in new_documents:
            try:
                message = self.format_document_message(doc, is_new=True)
                keyboard = self.create_document_keyboard(doc, 'regional')
                await update.message.reply_text(message, reply_markup=keyboard, disable_web_page_preview=True)
                
                # Добавляем в просмотренные
                self.add_seen_document('regional', doc['number'])
                
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                continue
        
        # Отправляем клавиатуру для дальнейших действий
        keyboard = self.create_back_keyboard('regional')
        await update.message.reply_text("✅ Проверка региональных документов завершена!\n\nВыберите следующее действие:", reply_markup=keyboard)

    async def show_federal_documents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает последние федеральные документы"""
        status_msg = await update.message.reply_text("🔍 Загружаю последние федеральные документы...")
        
        documents = self.parse_documents('federal')
        
        if documents is None:
            await status_msg.edit_text("❌ Ошибка при получении данных федеральных документов")
            keyboard = self.create_back_keyboard('federal')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        if not documents:
            await status_msg.edit_text("📭 Федеральные документы не найдены")
            keyboard = self.create_back_keyboard('federal')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        # Ограничиваем количество для вывода
        display_docs = documents[:5]
        
        await status_msg.edit_text(f"📚 Найдено {len(documents)} федеральных документов. Показываю последние {len(display_docs)}:")
        
        for doc in display_docs:
            try:
                message = self.format_document_message(doc, is_new=doc['is_new'])
                keyboard = self.create_document_keyboard(doc, 'federal')
                await update.message.reply_text(message, reply_markup=keyboard, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                continue
        
        # Отправляем клавиатуру для дальнейших действий
        keyboard = self.create_back_keyboard('federal')
        if len(documents) > 5:
            await update.message.reply_text(f"ℹ️ И еще {len(documents) - 5} федеральных документов...\n\nВыберите действие:", reply_markup=keyboard)
        else:
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)

    async def show_regional_documents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает последние региональные документы"""
        status_msg = await update.message.reply_text("🔍 Загружаю последние региональные документы...")
        
        documents = self.parse_documents('regional')
        
        if documents is None:
            await status_msg.edit_text("❌ Ошибка при получении данных региональных документов")
            keyboard = self.create_back_keyboard('regional')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        if not documents:
            await status_msg.edit_text("📭 Региональные документы не найдены")
            keyboard = self.create_back_keyboard('regional')
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)
            return
        
        # Ограничиваем количество для вывода
        display_docs = documents[:5]
        
        await status_msg.edit_text(f"📚 Найдено {len(documents)} региональных документов. Показываю последние {len(display_docs)}:")
        
        for doc in display_docs:
            try:
                message = self.format_document_message(doc, is_new=doc['is_new'])
                keyboard = self.create_document_keyboard(doc, 'regional')
                await update.message.reply_text(message, reply_markup=keyboard, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                continue
        
        # Отправляем клавиатуру для дальнейших действий
        keyboard = self.create_back_keyboard('regional')
        if len(documents) > 5:
            await update.message.reply_text(f"ℹ️ И еще {len(documents) - 5} региональных документов...\n\nВыберите действие:", reply_markup=keyboard)
        else:
            await update.message.reply_text("Выберите действие:", reply_markup=keyboard)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на инлайн-кнопки"""
        query = update.callback_query
        await query.answer()
        
        # Обработка скачивания PDF
        if query.data.startswith("download_"):
            parts = query.data.split("_")
            if len(parts) >= 3:
                doc_type = parts[1]
                document_number = "_".join(parts[2:])
                await self.download_pdf_callback(update, context, doc_type, document_number)

    async def download_pdf_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE, doc_type, document_number):
        """Обработчик скачивания PDF"""
        query = update.callback_query
        
        # Отправляем сообщение о начале скачивания
        status_msg = await query.message.reply_text(f"📥 Скачиваю PDF для документа {document_number}...")
        
        # Находим документ по номеру
        documents = self.parse_documents(doc_type)
        if not documents:
            await status_msg.edit_text("❌ Не удалось получить данные документов")
            return
        
        target_doc = None
        for doc in documents:
            if doc['number'] == document_number:
                target_doc = doc
                break
        
        if not target_doc or not target_doc['pdf']:
            await status_msg.edit_text("❌ PDF не найден")
            return
        
        # Скачиваем PDF
        pdf_content, filename = self.download_pdf(target_doc['pdf'], document_number)
        
        if pdf_content and filename:
            try:
                # Отправляем PDF как документ
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_content,
                    filename=filename,
                    caption=f"📄 {target_doc['name']}\n🔢 Номер: {document_number}\n🏛️ Тип: {'Федеральный' if doc_type == 'federal' else 'Региональный'}"
                )
                await status_msg.edit_text("✅ PDF успешно отправлен")
            except Exception as e:
                logger.error(f"Ошибка отправки PDF: {e}")
                await status_msg.edit_text("❌ Ошибка отправки PDF")
        else:
            await status_msg.edit_text("❌ Не удалось скачать PDF")

    def run(self):
        """Запуск бота"""
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("menu", self.show_main_menu))
        application.add_handler(CallbackQueryHandler(self.button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Бот запущен...")
        print("Бот запущен. Нажмите Ctrl+C для остановки.")
        application.run_polling()

if __name__ == '__main__':
    bot = DocumentBot()

    bot.run()
