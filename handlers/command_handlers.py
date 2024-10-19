# handlers/command_handlers.py
from telebot import types
from telebot.types import Message
from utils.data_manager import load_data, save_data, init_user
from utils.navigation import navigate_to_path
from utils.keyboards import generate_markup
import uuid
import telebot

def register_command_handlers(bot: telebot.TeleBot):
    @bot.message_handler(commands=['start'])
    def handle_start(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)
        save_data(data)
        bot.send_message(message.chat.id, "Добро пожаловать! Используйте команды для управления вашими данными.\n\n"
                                          "/mkdir <имя_папки> - Создать новую папку\n"
                                          "/cd <имя_папки> - Перейти в папку\n"
                                          "/up - Вернуться на уровень выше\n"
                                          "/getmydata - Показать текущую папку и все файлы\n"
                                          "/share - Сделать текущую папку публичной\n"
                                          "/access <ключ> - Доступ к публичной папке по ключу")

    @bot.message_handler(commands=['mkdir'])
    def handle_mkdir(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, folder_name = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Пожалуйста, укажите имя папки. Пример: /mkdir МояПапка")
            return

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
        if folder_name in current["folders"]:
            bot.reply_to(message, "Папка с таким именем уже существует.")
        else:
            current["folders"][folder_name] = {"folders": {}, "files": []}
            save_data(data)
            bot.reply_to(message, f"Папка '{folder_name}' создана.")

    @bot.message_handler(commands=['cd'])
    def handle_cd(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, folder_name = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Пожалуйста, укажите имя папки. Пример: /cd МояПапка")
            return

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])
        if folder_name in current["folders"]:
            data["users"][user_id]["current_path"].append(folder_name)
            save_data(data)
            bot.reply_to(message, f"Перешли в папку '{folder_name}'.")
        else:
            bot.reply_to(message, "Папка не найдена.")

    @bot.message_handler(commands=['up'])
    def handle_up(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        if data["users"][user_id]["current_path"]:
            popped = data["users"][user_id]["current_path"].pop()
            save_data(data)
            bot.reply_to(message, f"Вернулись из папки '{popped}'.")
        else:
            bot.reply_to(message, "Вы уже в корневой папке.")

    @bot.message_handler(commands=['getmydata'])
    def handle_getmydata(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        current = navigate_to_path(data["users"][user_id]["structure"], data["users"][user_id]["current_path"])

        markup = generate_markup(current, data["users"][user_id]["current_path"])

        try:
            bot.send_message(message.chat.id, "Ваша папочная структура:", reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке клавиатуры: {str(e)}")

    @bot.message_handler(commands=['share'])
    def handle_share(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        current_path = data["users"][user_id]["current_path"]
        structure = data["users"][user_id]["structure"]

        # Навигация до текущей папки
        try:
            current = navigate_to_path(structure, current_path)
        except KeyError:
            bot.reply_to(message, "Текущая папка не существует.")
            return

        # Генерация уникального ключа
        unique_key = uuid.uuid4().hex  # Генерирует 32-символьный уникальный ключ

        # Сохранение связи ключа с пользователем и путем
        data["shared_folders"][unique_key] = {
            "user_id": user_id,
            "path": current_path.copy()
        }

        save_data(data)

        # Отправка ключа пользователю
        bot.reply_to(message, f"Папка успешно сделана публичной.\nВаш ключ для доступа: `{unique_key}`\nИспользуйте команду /access <ключ> чтобы получить доступ.", parse_mode="Markdown")

    @bot.message_handler(commands=['access'])
    def handle_access(message: Message):
        user_id = str(message.chat.id)
        data = load_data()
        init_user(data, user_id)

        try:
            _, access_key = message.text.split(maxsplit=1)
        except ValueError:
            bot.reply_to(message, "Пожалуйста, укажите ключ доступа. Пример: /access <ключ>")
            return

        shared = data.get("shared_folders", {}).get(access_key)
        if not shared:
            bot.reply_to(message, "Неверный или несуществующий ключ доступа.")
            return

        owner_id = shared["user_id"]
        path = shared["path"]

        # Проверка, существует ли пользователь и папка
        if owner_id not in data["users"]:
            bot.reply_to(message, "Владелец папки не существует.")
            return

        owner_structure = data["users"][owner_id]["structure"]
        try:
            shared_folder = navigate_to_path(owner_structure, path)
        except KeyError:
            bot.reply_to(message, "Папка не найдена.")
            return

        # Генерация клавиатуры для публичной папки
        markup = generate_markup(shared_folder, path, shared_key=access_key)

        try:
            bot.send_message(message.chat.id, "Содержимое публичной папки:", reply_markup=markup)
        except telebot.apihelper.ApiTelegramException as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке клавиатуры: {str(e)}")
