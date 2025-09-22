import os
import logging
from datetime import datetime

from dotenv import load_dotenv
import telebot
from flask import Flask, request

# =========================
#   ЗАГРУЗКА КОНФИГА
# =========================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOLDER_ID = os.getenv("FOLDER_ID")          # если используешь YandexGPT
API_KEY = os.getenv("API_KEY")              # если используешь YandexGPT
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in ADMIN_IDS.split(",") if x.strip().isdigit()]

# URL твоего сервиса на Render (External URL, из Dashboard → Settings → Environment)
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")    # пример: https://telegram-bot-xxxxx.onrender.com
WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_TOKEN не задан. Проверь переменные окружения.")

# =========================
#     ИНИЦИАЛИЗАЦИЯ
# =========================
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Простая «статистика» в памяти процесса
user_stats = {}

# =========================
#       ХЭНДЛЕРЫ
# =========================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    user_stats[uid] = user_stats.get(uid, 0) + 1
    bot.reply_to(message, "👋 Привет! Я бот 🤖. Напиши что-нибудь, и я отвечу.")

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.reply_to(
        message,
        "📌 Команды:\n"
        "/start — начать\n"
        "/help — помощь\n"
        "/admin — панель администратора (если есть права)\n"
        "/stats — статистика (для админов)"
    )

@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if message.from_user.id in ADMIN_IDS:
        bot.reply_to(message, "✅ У вас есть права администратора!")
    else:
        bot.reply_to(message, "❌ У вас нет прав администратора.")

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Доступ запрещён")
        return
    total_users = len(user_stats)
    total_messages = sum(user_stats.values())
    bot.reply_to(
        message,
        f"📊 Статистика:\n"
        f"👥 Пользователей: {total_users}\n"
        f"💬 Сообщений: {total_messages}\n"
        f"🕒 Серверное время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

@bot.message_handler(func=lambda m: True)
def echo(message):
    uid = message.from_user.id
    user_stats[uid] = user_stats.get(uid, 0) + 1
    bot.reply_to(message, f"Ты написал: {message.text}")

# =========================
#      FLASK РОУТЫ
# =========================
@app.get("/")
def index():
    return "OK", 200

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.post(WEBHOOK_PATH)
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    return "Unsupported Media Type", 415

# =========================
#       ЗАПУСК APP
# =========================
if __name__ == "__main__":
    if not WEBHOOK_URL:
        raise RuntimeError(
            "❌ WEBHOOK_HOST не задан. Добавь переменную окружения в Render → "
            "Settings → Environment → WEBHOOK_HOST=https://<твой-сервис>.onrender.com"
        )

    logging.info("Удаляем старый webhook (на всякий случай)...")
    bot.remove_webhook()

    logging.info(f"Ставим новый webhook: {WEBHOOK_URL}")
    ok = bot.set_webhook(url=WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Webhook set: {ok}")

    port = int(os.environ.get("PORT", 5000))
    logging.info(f"Запускаем Flask на 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
