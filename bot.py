import os
import requests
import logging
from collections import defaultdict
from dotenv import load_dotenv
import telebot

# Загружаем переменные окружения из .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")
API_KEY = os.getenv("API_KEY")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="bot.log"
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Хранилище контекста (последние 5 сообщений для каждого чата)
chat_context = defaultdict(list)

# Команда /start
@bot.message_handler(commands=["start"])
def start_message(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Привет! Я бот на YandexGPT 🤖. Задавай вопросы!\n/help — помощь.")
    logger.info(f"Пользователь {chat_id} запустил бота.")

# Команда /help
@bot.message_handler(commands=["help"])
def help_message(message):
    chat_id = message.chat.id
    help_text = (
        "Команды:\n"
        "/start — начать работу\n"
        "/help — показать помощь\n"
        "/clear — очистить контекст\n"
        "/ping — проверить доступность YandexGPT\n"
    )
    bot.send_message(chat_id, help_text)
    logger.info(f"Пользователь {chat_id} запросил помощь.")

# Команда /clear
@bot.message_handler(commands=["clear"])
def clear_context(message):
    chat_id = message.chat.id
    chat_context[chat_id].clear()
    bot.send_message(chat_id, "Контекст диалога очищен ✅")
    logger.info(f"Контекст очищен для {chat_id}")

# Команда /ping — health-check
@bot.message_handler(commands=["ping"])
def ping(message):
    chat_id = message.chat.id
    try:
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 10},
            "messages": [{"role": "user", "text": "ping"}]
        }
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            bot.send_message(chat_id, "✅ YandexGPT доступен!")
        else:
            bot.send_message(chat_id, f"⚠️ Ошибка API: {response.status_code}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при проверке: {str(e)}")

# Обработка обычных сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    try:
        # Добавляем сообщение в контекст
        chat_context[chat_id].append({"role": "user", "text": message.text})

        # Формируем контекст (последние 5 сообщений + system prompt)
        messages = [{"role": "system", "text": "Ты полезный ассистент. Отвечай кратко и по делу."}] + chat_context[chat_id][-5:]

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 500},
            "messages": messages
        }

        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            answer = result["result"]["alternatives"][0]["message"]["text"]
            bot.reply_to(message, answer)

            # Добавляем ответ в контекст
            chat_context[chat_id].append({"role": "assistant", "text": answer})
            logger.info(f"Ответ {chat_id}: {answer[:50]}...")
        else:
            bot.reply_to(message, f"⚠️ Ошибка API: {response.status_code} - {response.text}")
            logger.error(f"Ошибка API {chat_id}: {response.text}")

    except requests.exceptions.Timeout:
        bot.reply_to(message, "⚠️ Таймаут: сервер долго не отвечает.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")
        logger.error(f"Ошибка у {chat_id}: {str(e)}")

if __name__ == "__main__":
    logger.info("Бот запускается...")
    print("Бот запускается...")
    bot.polling(none_stop=True)
