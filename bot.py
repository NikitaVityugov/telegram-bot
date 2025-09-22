import os
import json
import telebot
from dotenv import load_dotenv
from flask import Flask, request
import requests
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

STATS_FILE = "stats.json"

# =======================
# Работа со статистикой
# =======================

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "messages": 0}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

stats = load_stats()

def update_stats(user_id):
    stats["messages"] += 1
    stats["users"].setdefault(str(user_id), 0)
    stats["users"][str(user_id)] += 1
    save_stats(stats)

# =======================
# Вспомогательные функции
# =======================

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

def ask_yandex_gpt(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 200
        },
        "messages": [
            {"role": "user", "text": prompt}
        ]
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        result = resp.json()
        try:
            return result["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError):
            return "⚠️ Ошибка разбора ответа YandexGPT"
    else:
        return f"⚠️ Ошибка API: {resp.status_code} - {resp.text}"

# =======================
# Команды
# =======================

@bot.message_handler(commands=["start"])
def start_message(message):
    bot.reply_to(message, "👋 Привет! Я бот 🤖. Напиши что-нибудь, и я отвечу через YandexGPT.")

@bot.message_handler(commands=["help"])
def help_message(message):
    help_text = (
        "📌 Доступные команды:\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/ping — проверить доступность YandexGPT\n"
        "/admin — панель администратора (только для админов)"
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=["ping"])
def ping_message(message):
    test = ask_yandex_gpt("Скажи 'Привет' одним словом.")
    bot.reply_to(message, f"✅ YandexGPT доступен: {test}")

@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ У тебя нет доступа к админ-панели.")
        return
    panel = (
        "⚙️ Панель администратора:\n"
        "/stats — статистика\n"
        "/users — список пользователей\n"
        "/broadcast — рассылка"
    )
    bot.reply_to(message, panel)

@bot.message_handler(commands=["stats"])
def show_stats(message):
    if not is_admin(message.from_user.id):
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reply = (
        f"📊 Статистика:\n"
        f"- Пользователей: {len(stats['users'])}\n"
        f"- Сообщений: {stats['messages']}\n"
        f"- Время сервера: {now}"
    )
    bot.reply_to(message, reply)

@bot.message_handler(commands=["users"])
def list_users(message):
    if not is_admin(message.from_user.id):
        return
    reply = "👥 Список пользователей:\n"
    for uid, count in stats["users"].items():
        reply += f"ID: {uid} — {count} сообщений\n"
    bot.reply_to(message, reply)

@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(" ", 1)
    if len(parts) < 2:
        bot.reply_to(message, "✍️ Использование: /broadcast текст рассылки")
        return
    text = parts[1]
    for uid in stats["users"].keys():
        try:
            bot.send_message(uid, f"📢 Сообщение от админа:\n\n{text}")
        except Exception:
            pass
    bot.reply_to(message, "✅ Рассылка завершена.")

# =======================
# Основная логика
# =======================

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    update_stats(message.from_user.id)
    reply = ask_yandex_gpt(message.text)
    bot.reply_to(message, reply)

# =======================
# Flask + Webhook
# =======================

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Бот работает!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_URL')}/{TELEGRAM_TOKEN}")
    app.run(host="0.0.0.0", port=port)
