import os
import telebot
from telebot import types
from dotenv import load_dotenv
from datetime import datetime

# ==================
#   ЗАГРУЗКА КЛЮЧЕЙ
# ==================
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
API_KEY = os.getenv("YANDEX_API_KEY")

# Админы (список ID через запятую)
ADMIN_IDS = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in ADMIN_IDS.split(",") if x.strip().isdigit()]

# Создаём экземпляр бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Хранилище статистики
user_stats = {}


# ==================
#  ОБЫЧНЫЕ КОМАНДЫ
# ==================
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    user_stats[user_id] = user_stats.get(user_id, 0) + 1
    bot.reply_to(message, "👋 Привет! Я бот 🤖. Напиши что-нибудь, и я отвечу.")


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.reply_to(message,
                 "📌 Доступные команды:\n"
                 "/start — запуск\n"
                 "/help — помощь\n"
                 "/ping — проверить доступность YandexGPT\n"
                 "/admin — панель администратора (только для админов)")


@bot.message_handler(commands=['ping'])
def ping_message(message):
    # Пока просто эхо-ответ
    bot.reply_to(message, "✅ YandexGPT доступен (тестовый ответ).")


# ==================
#   АДМИН-КОМАНДЫ
# ==================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id in ADMIN_IDS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("/stats", "/users", "/broadcast")
        bot.reply_to(message, "⚙️ Панель администратора:", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ У вас нет прав администратора.")


@bot.message_handler(commands=['stats'])
def stats_message(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Доступ запрещён")
        return
    total_users = len(user_stats)
    total_messages = sum(user_stats.values())
    bot.reply_to(
        message,
        f"📊 Статистика:\n"
        f"- Пользователей: {total_users}\n"
        f"- Сообщений: {total_messages}\n"
        f"- Время сервера: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Доступ запрещён")
        return
    if not user_stats:
        bot.reply_to(message, "👥 Пользователей пока нет.")
        return
    users_list = "\n".join([f"ID: {uid} — {count} сообщений" for uid, count in user_stats.items()])
    bot.reply_to(message, f"👥 Список пользователей:\n{users_list}")


@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Доступ запрещён")
        return
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        bot.reply_to(message, "✍️ Использование: `/broadcast текст рассылки`", parse_mode="Markdown")
        return
    sent = 0
    for uid in user_stats.keys():
        try:
            bot.send_message(uid, f"📢 Сообщение от администратора:\n\n{text}")
            sent += 1
        except Exception as e:
            print(f"Не удалось отправить {uid}: {e}")
    bot.reply_to(message, f"✅ Рассылка завершена. Доставлено {sent} пользователям.")


# ==================
#    ЭХО-ОТВЕТ
# ==================
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    user_id = message.from_user.id
    user_stats[user_id] = user_stats.get(user_id, 0) + 1
    bot.reply_to(message, f"Ты написал: {message.text}")


# ==================
#    ЗАПУСК БОТА
# ==================
if __name__ == "__main__":
    print("Бот запускается...")
    bot.polling(none_stop=True)
