# bot.py

import telebot
import config
from utils.data_manager import load_data, save_data
from handlers.command_handlers import register_command_handlers
from handlers.callback_handlers import register_callback_handlers
from handlers.message_handlers import register_message_handlers
import time
import requests
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Установите уровень на DEBUG для подробного логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def start_bot():
    bot = telebot.TeleBot(config.BOT_TOKEN)

    # Регистрация обработчиков
    register_command_handlers(bot)
    register_callback_handlers(bot)
    register_message_handlers(bot)

    # Запуск бота с увеличенным timeout и обработкой исключений
    while True:
        try:
            logger.info("Бот запущен и ожидает обновлений...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except requests.exceptions.ReadTimeout:
            logger.warning("ReadTimeoutError: Превышено время ожидания. Попытка перезапуска polling...")
            time.sleep(5)  # Пауза перед повторной попыткой
        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
