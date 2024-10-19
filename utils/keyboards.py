# utils/keyboards.py

from telebot import types
import uuid

def generate_callback_data(prefix, *args):
    """
    Генерирует безопасный callback_data, сохраняя допустимые символы и ограничивая длину.
    """
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")
    safe_args = []
    for arg in args:
        safe_arg = ''.join(e for e in arg if e in allowed_chars)
        safe_args.append(safe_arg[:20])  # Ограничиваем длину каждого аргумента
    callback = f"{prefix}:" + ":".join(safe_args)
    return callback

def generate_markup(current, path, shared_key=None):
    markup = types.InlineKeyboardMarkup()
    
    # Кнопка "Вверх", если не в корневой папке
    if path:
        if shared_key:
            callback_data = generate_callback_data("shared_up", shared_key)
        else:
            callback_data = "up"
        markup.add(types.InlineKeyboardButton("⬆️ Вверх", callback_data=callback_data))

    # Кнопки папок
    for folder in current["folders"]:
        if shared_key:
            callback_data = generate_callback_data("shared_folder", shared_key, folder)
        else:
            callback_data = generate_callback_data("folder", folder)
        markup.add(types.InlineKeyboardButton(f"📁 {folder}", callback_data=callback_data))

    # Кнопки файлов
    for idx, file in enumerate(current["files"], start=1):
        if file["type"] == "text":
            display_name = f"📝 Текст {idx}"
        elif file["type"] == "document":
            display_name = f"📄 Документ {idx}"
        elif file["type"] == "photo":
            display_name = f"🖼️ Фото {idx}"
        elif file["type"] == "video":
            display_name = f"🎬 Видео {idx}"
        elif file["type"] == "audio":
            display_name = f"🎵 Аудио {idx}"
        else:
            display_name = f"📁 Файл {idx}"

        if shared_key:
            callback_data = generate_callback_data("shared_file", shared_key, file["file_id"])
        else:
            callback_data = generate_callback_data("file", file["file_id"])
        markup.add(types.InlineKeyboardButton(display_name, callback_data=callback_data))
    
    # Добавляем кнопку "Retrieve All"
    if shared_key:
        callback_data = generate_callback_data("shared_retrieve_all", shared_key)
    else:
        callback_data = "retrieve_all"
    markup.add(types.InlineKeyboardButton("📤 Вернуть Все", callback_data=callback_data))

    return markup
