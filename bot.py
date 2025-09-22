import os
import telebot
from telebot import types
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime

# Загружаем .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# ==============================
# Хранилище статистики
# ==============================
user_stats = {}
total_messages = 0

# ==============================
# Команды
# ==============================
@bot.message_handler(commands=["start"])
def start_cmd(message):
    bot.reply_to(message, "👋 Привет! Я бот 🤖. Напиши что-нибудь, и я отвечу.")

@bot.message_handler(commands=["help"])
def help_cmd(message):
    bot.reply_to(message, "📌 Доступные команды:\n"
                          "/start — запуск\n"
                          "/help — помощь\n"
                          "/ping — проверить доступность YandexGPT\n"
                          "/admin — панель администратора (только для админов)")

@bot.message_handler(commands=["ping"])
def ping_cmd(message):
    bot.reply_to(message, "✅ YandexGPT доступен (тестовый ответ).")

@bot.message_handler(commands=["admin"])
def admin_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ У тебя нет прав для этого.")
        return
    bot.reply_to(message, "⚙️ Панель администратора:\n"
                          "/stats — статистика\n"
                          "/users — список пользователей\n"
                          "/broadcast <текст> — рассылка")

@bot.message_handler(commands=["stats"])
def stats_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    global total_messages
    server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bot.reply_to(message, f"📊 Статистика:\n"
                          f"- Пользователей: {len(user_stats)}\n"
                          f"- Сообщений: {total_messages}\n"
                          f"- Время сервера: {server_time}")

@bot.message_handler(commands=["users"])
def users_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = "👥 Список пользователей:\n"
    for user_id, count in user_stats.items():
        text += f"ID: {user_id} — {count} сообщений\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Использование: /broadcast текст рассылки")
        return
    text = parts[1]
    for user_id in user_stats.keys():
        try:
            bot.send_message(user_id, f"📢 Рассылка:\n{text}")
        except Exception:
            pass
    bot.reply_to(message, "✅ Рассылка завершена.")

# ==============================
# Ответы на обычные сообщения
# ==============================
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    global total_messages
    user_id = message.from_user.id
    user_stats[user_id] = user_stats.get(user_id, 0) + 1
    total_messages += 1
    bot.reply_to(message, f"Ты написал: {message.text}")

# ==============================
# Flask (для Render)
# ==============================
@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Бот работает!", 200

# ==============================
# Запуск
# ==============================
if __name__ == "__main__":
    # Устанавливаем webhook
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_TOKEN}")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
