# handlers/callback_handlers.py

from telebot.types import CallbackQuery
from utils.data_manager import load_data, save_data, init_user
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import telebot
import logging

logger = logging.getLogger(__name__)

def register_callback_handlers(bot: telebot.TeleBot):
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call: CallbackQuery):
        user_id = str(call.message.chat.id)
        data = load_data()
        init_user(data, user_id)

        if call.data.startswith("shared_"):
            handle_shared_callback(call, data)
            return

        # Оригинальная обработка для личных папок
        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])

        if call.data == "up":
            if data["users"][user_id]["current_path"]:
                popped = data["users"][user_id]["current_path"].pop()
                bot.answer_callback_query(call.id, f"Вернулись из папки '{popped}'.")
            else:
                bot.answer_callback_query(call.id, "Вы уже в корневой папке.")
        elif call.data.startswith("folder:"):
            folder_name = call.data.split(":", 1)[1]
            if folder_name in current["folders"]:
                data["users"][user_id]["current_path"].append(folder_name)
                bot.answer_callback_query(call.id, f"Перешли в папку '{folder_name}'.")
            else:
                bot.answer_callback_query(call.id, "Папка не найдена.")
        elif call.data.startswith("file:"):
            short_id = call.data.split(":", 1)[1]
            file_id = data["users"][user_id]["file_mappings"].get(short_id)
            if not file_id:
                bot.answer_callback_query(call.id, "Файл не найден.")
                return
            # Найдём файл по short_id в текущей папке
            file = next((f for f in current["files"] if f.get("short_id") == short_id), None)
            if file:
                try:
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file["file_id"])
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file["file_id"])
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file["file_id"])
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file["file_id"])
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                    bot.answer_callback_query(call.id, "Файл отправлен.")
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла: {e}")
                    bot.answer_callback_query(call.id, f"Ошибка при отправке файла: {str(e)}")
            else:
                bot.answer_callback_query(call.id, "Файл не найден.")
        elif call.data.startswith("retrieve_all"):
            # Обработка возврата всех сообщений и файлов в текущей папке
            try:
                for file in current["files"]:
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file["file_id"])
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file["file_id"])
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file["file_id"])
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file["file_id"])
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                bot.answer_callback_query(call.id, "Все файлы отправлены.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файлов: {e}")
                bot.answer_callback_query(call.id, f"Ошибка при отправке файлов: {str(e)}")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда.")

        # Обновляем папочную структуру после действия, если это необходимо
        if call.data.startswith("folder:") or call.data == "up":
            current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
            markup = generate_markup(current, data["users"][user_id]["current_path"])
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка обновления клавиатуры: {str(e)}")

        save_data(data)

    def handle_shared_callback(call: CallbackQuery, data: dict):
        user_id = str(call.message.chat.id)

        # Разбор callback_data
        parts = call.data.split(":")
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Неверный формат команды.")
            return

        command = parts[0]

        if command == "shared_up":
            shared_key = parts[1]
            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            # В текущей реализации навигация по публичным папкам ограничена
            bot.answer_callback_query(call.id, "Навигация по публичным папкам пока не поддерживается.")

        elif command == "shared_folder":
            if len(parts) < 3:
                bot.answer_callback_query(call.id, "Неверный формат команды для папки.")
                return
            shared_key = parts[1]
            folder_name = parts[2]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            if folder_name not in shared_folder["folders"]:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Обновляем путь для навигации внутри публичной папки
            new_shared_path = base_path + [folder_name]
            try:
                current = navigate_to_path(owner_structure, new_shared_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Генерация клавиатуры для новой папки
            markup = generate_markup(current, new_shared_path, shared_key=shared_key)

            # Редактирование сообщения с новой клавиатурой
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
                bot.answer_callback_query(call.id, f"Перешли в публичную папку '{folder_name}'.")
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.answer_callback_query(call.id, f"Ошибка обновления клавиатуры: {str(e)}")

        elif command == "shared_file":
            if len(parts) < 3:
                bot.answer_callback_query(call.id, "Неверный формат команды для файла.")
                return
            shared_key = parts[1]
            short_id = parts[2]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Найдём файл по short_id в текущей папке
            file = next((f for f in shared_folder["files"] if f.get("short_id") == short_id), None)
            if file:
                file_id = data["users"][owner_id]["file_mappings"].get(short_id)
                if not file_id:
                    bot.answer_callback_query(call.id, "Файл не найден.")
                    return
                try:
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file_id)
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file_id)
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file_id)
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file_id)
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                    bot.answer_callback_query(call.id, "Файл отправлен.")
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла: {e}")
                    bot.answer_callback_query(call.id, f"Ошибка при отправке файла: {str(e)}")
            else:
                bot.answer_callback_query(call.id, "Файл не найден.")

        elif command == "shared_retrieve_all":
            if len(parts) < 2:
                bot.answer_callback_query(call.id, "Неверный формат команды для получения всех файлов.")
                return
            shared_key = parts[1]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Отправка всех файлов в текущей папке
            try:
                for file in shared_folder["files"]:
                    short_id = file.get("short_id")
                    if not short_id:
                        continue  # Или обработать ошибку
                    file_id = data["users"][owner_id]["file_mappings"].get(short_id)
                    if not file_id:
                        continue  # Или обработать ошибку
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file_id)
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file_id)
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file_id)
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file_id)
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                bot.answer_callback_query(call.id, "Все файлы отправлены.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файлов: {e}")
                bot.answer_callback_query(call.id, f"Ошибка при отправке файлов: {str(e)}")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда для публичных папок.")

        # Обновляем папочную структуру после действия, если это необходимо
        if call.data.startswith("folder:") or call.data == "up":
            current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
            markup = generate_markup(current, data["users"][user_id]["current_path"])
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка обновления клавиатуры: {str(e)}")

        save_data(data)

    def handle_shared_callback(call: CallbackQuery, data: dict):
        user_id = str(call.message.chat.id)

        # Разбор callback_data
        parts = call.data.split(":")
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Неверный формат команды.")
            return

        command = parts[0]

        if command == "shared_up":
            shared_key = parts[1]
            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            # В текущей реализации навигация по публичным папкам ограничена
            bot.answer_callback_query(call.id, "Навигация по публичным папкам пока не поддерживается.")

        elif command == "shared_folder":
            if len(parts) < 3:
                bot.answer_callback_query(call.id, "Неверный формат команды для папки.")
                return
            shared_key = parts[1]
            folder_name = parts[2]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            if folder_name not in shared_folder["folders"]:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Обновляем путь для навигации внутри публичной папки
            new_shared_path = base_path + [folder_name]
            try:
                current = navigate_to_path(owner_structure, new_shared_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Генерация клавиатуры для новой папки
            markup = generate_markup(current, new_shared_path, shared_key=shared_key)

            # Редактирование сообщения с новой клавиатурой
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
                bot.answer_callback_query(call.id, f"Перешли в публичную папку '{folder_name}'.")
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.answer_callback_query(call.id, f"Ошибка обновления клавиатуры: {str(e)}")

        elif command == "shared_file":
            if len(parts) < 3:
                bot.answer_callback_query(call.id, "Неверный формат команды для файла.")
                return
            shared_key = parts[1]
            short_id = parts[2]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Найдём файл по short_id в текущей папке
            file = next((f for f in shared_folder["files"] if f.get("short_id") == short_id), None)
            if file:
                file_id = data["users"][owner_id]["file_mappings"].get(short_id)
                if not file_id:
                    bot.answer_callback_query(call.id, "Файл не найден.")
                    return
                try:
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file_id)
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file_id)
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file_id)
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file_id)
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                    bot.answer_callback_query(call.id, "Файл отправлен.")
                except Exception as e:
                    logger.error(f"Ошибка при отправке файла: {e}")
                    bot.answer_callback_query(call.id, f"Ошибка при отправке файла: {str(e)}")
            else:
                bot.answer_callback_query(call.id, "Файл не найден.")

        elif command == "shared_retrieve_all":
            if len(parts) < 2:
                bot.answer_callback_query(call.id, "Неверный формат команды для получения всех файлов.")
                return
            shared_key = parts[1]

            shared = data.get("shared_folders", {}).get(shared_key)
            if not shared:
                bot.answer_callback_query(call.id, "Неверный ключ доступа.")
                return

            owner_id = shared["user_id"]
            base_path = shared["path"]

            owner_structure = data["users"].get(owner_id, {}).get("structure")
            if not owner_structure:
                bot.answer_callback_query(call.id, "Структура папки не найдена.")
                return

            try:
                shared_folder = navigate_to_path(owner_structure, base_path)
            except KeyError:
                bot.answer_callback_query(call.id, "Папка не найдена.")
                return

            # Отправка всех файлов в текущей папке
            try:
                for file in shared_folder["files"]:
                    short_id = file.get("short_id")
                    if not short_id:
                        continue  # Или обработать ошибку
                    file_id = data["users"][owner_id]["file_mappings"].get(short_id)
                    if not file_id:
                        continue  # Или обработать ошибку
                    if file["type"] == "text":
                        bot.send_message(call.message.chat.id, f"Текст: {file['content']}")
                    elif file["type"] == "document":
                        bot.send_document(chat_id=call.message.chat.id, document=file_id)
                    elif file["type"] == "photo":
                        bot.send_photo(chat_id=call.message.chat.id, photo=file_id)
                    elif file["type"] == "video":
                        bot.send_video(chat_id=call.message.chat.id, video=file_id)
                    elif file["type"] == "audio":
                        bot.send_audio(chat_id=call.message.chat.id, audio=file_id)
                    else:
                        bot.send_message(call.message.chat.id, "Неизвестный тип файла.")
                bot.answer_callback_query(call.id, "Все файлы отправлены.")
            except Exception as e:
                logger.error(f"Ошибка при отправке файлов: {e}")
                bot.answer_callback_query(call.id, f"Ошибка при отправке файлов: {str(e)}")
        else:
            bot.answer_callback_query(call.id, "Неизвестная команда для публичных папок.")

        # Обновляем папочную структуру после действия, если это необходимо
        if call.data.startswith("folder:") or call.data == "up":
            current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
            markup = generate_markup(current, data["users"][user_id]["current_path"])
            try:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id,
                                              message_id=call.message.message_id,
                                              reply_markup=markup)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" in str(e):
                    # Игнорируем ошибку, если сообщение не изменилось
                    pass
                else:
                    logger.error(f"Ошибка обновления клавиатуры: {e}")
                    bot.send_message(call.message.chat.id, f"Ошибка обновления клавиатуры: {str(e)}")

        save_data(data)
