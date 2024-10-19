# handlers/message_handlers.py

from telebot.types import Message
from utils.data_manager import load_data, save_data, init_user
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import telebot
import uuid  # Для генерации уникальных short_id
import logging

logger = logging.getLogger(__name__)

def register_message_handlers(bot: telebot.TeleBot):
    @bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio'])
    def handle_message(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        # Игнорируем команды
        if message.content_type == 'text' and message.text.startswith('/'):
            return

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])

        if message.content_type == 'text':
            # Сохраняем текст как файл типа 'text'
            current["files"].append({"type": "text", "content": message.text})
            save_data(data)
            bot.reply_to(message, "Текстовое сообщение сохранено в текущей папке.")
        elif message.content_type == 'document':
            file_id = message.document.file_id
            short_id = uuid.uuid4().hex[:8]  # Генерация короткого уникального ID
            current["files"].append({"type": "document", "file_id": file_id, "file_name": message.document.file_name, "short_id": short_id})
            data["users"][user_id]["file_mappings"][short_id] = file_id  # Сохраняем сопоставление
            save_data(data)
            bot.reply_to(message, "Документ сохранён в текущей папке.")
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            short_id = uuid.uuid4().hex[:8]
            current["files"].append({"type": "photo", "file_id": file_id, "short_id": short_id})
            data["users"][user_id]["file_mappings"][short_id] = file_id
            save_data(data)
            bot.reply_to(message, "Фото сохранено в текущей папке.")
        elif message.content_type == 'video':
            file_id = message.video.file_id
            short_id = uuid.uuid4().hex[:8]
            current["files"].append({"type": "video", "file_id": file_id, "short_id": short_id})
            data["users"][user_id]["file_mappings"][short_id] = file_id
            save_data(data)
            bot.reply_to(message, "Видео сохранено в текущей папке.")
        elif message.content_type == 'audio':
            file_id = message.audio.file_id
            short_id = uuid.uuid4().hex[:8]
            current["files"].append({"type": "audio", "file_id": file_id, "short_id": short_id})
            data["users"][user_id]["file_mappings"][short_id] = file_id
            save_data(data)
            bot.reply_to(message, "Аудио сохранено в текущей папке.")
        else:
            bot.reply_to(message, "Неизвестный тип контента.")
