import asyncio
import json
import os
import re
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from schedule_parser import parse_schedule, format_lesson

load_dotenv()
TOKEN = os.getenv("TOKEN")
USERS_FILE = "users.json"
CACHE_FILE = "cache.json"

WEEKDAYS_RU = {
    0: "Пнд", 1: "Втр", 2: "Срд",
    3: "Чтв", 4: "Птн", 5: "Сбт"
}

JOKES = [
    "Штирлиц шёл по коридору. Навстречу шёл Мюллер.\n— Штирлиц, вы шпион?\n— Нет.\n— Верю, — сказал Мюллер. — Шпионы так не одеваются.",
    "— Доктор, я буду жить?\n— А смысл?",
    "Муж приходит домой и видит жену с чемоданом.\n— Ты куда?\n— От тебя ухожу!\n— А я думал, ты возвращаешься.",
    "Программист заходит в бар, заказывает 1 пиво, 0 пива, 999999 пива, -1 пиво, NULL пива, выходит через служебный вход.",
    "— Как дела?\n— Как у всех.\n— Плохо?\n— Нет, не знаю как у всех, но у меня плохо.",
    "Студент сдаёт экзамен:\n— Билет 1. Всё знаю!\n— Билет 2. Всё знаю!\n— Билет 3. Ничего не знаю.\n— Странно...\n— Я только первые два учил.",
    "— Почему ты опоздал?\n— Будильник не зазвонил.\n— Почему?\n— Я его не завёл.\n— Почему?\n— Я знал, что опоздаю.",
    "Встречаются два студента:\n— Ты на лекцию?\n— Нет, я так хожу.",
    "— Сколько программистов нужно, чтобы вкрутить лампочку?\n— Ни одного, это проблема железа.",
    "Преподаватель: — Кто не сдаст зачёт, того отчислю!\nСтудент: — А кто сдаст?\nПреподаватель: — Тех удивлюсь.",
]

def get_random_joke() -> str:
    return random.choice(JOKES)

def get_joke_from_site() -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        resp = requests.get("https://anekdoty.ru/pro-shtirlica/", timeout=5)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("li .holder-body p")
        if items:
            item = random.choice(items)
            return item.get_text(separator="\n").strip()
    except Exception as e:
        print(f"Ошибка парсинга анекдота: {e}")
    return get_random_joke()

last_request = {}
COOLDOWN = 30

def is_rate_limited(chat_id: int) -> bool:
    now = datetime.now()
    if chat_id in last_request:
        if now - last_request[chat_id] < timedelta(seconds=COOLDOWN):
            return True
    last_request[chat_id] = now
    return False

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

def get_lessons_for_date(schedule, target_date):
    abbr = WEEKDAYS_RU.get(target_date.weekday())
    if not abbr:
        return None, {}
    for key, lessons in schedule.items():
        if key.startswith(abbr):
            date_match = re.search(r'(\d+)', key)
            if date_match and int(date_match.group(1)) == target_date.day:
                return key, lessons
    return None, {}


def get_today_lessons(schedule):
    today = datetime.now(ZoneInfo("Europe/Moscow"))
    return get_lessons_for_date(schedule, today)


def get_tomorrow_lessons(schedule):
    tomorrow = datetime.now(ZoneInfo("Europe/Moscow")) + timedelta(days=1)
    return get_lessons_for_date(schedule, tomorrow)


def build_message(day, lessons, empty_text="Сегодня пар нет 🎉"):
    if not lessons:
        return f"📅 {day}\n\n{empty_text}"
    parts = [f"📅 {day}"]
    for num, lesson in sorted(lessons.items()):
        parts.append(format_lesson(num, lesson))
    return "\n\n".join(parts)

async def broadcast(bot: Bot, message: str):
    users = load_users()
    print(f"Рассылка для {len(users)} пользователей")
    for chat_id in users:
        try:
            await bot.send_message(chat_id, message)
        except Exception as e:
            print(f"Ошибка {chat_id}: {e}")

async def send_daily_schedule(bot: Bot):
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        return
    await broadcast(bot, build_message(day, lessons))
    joke = get_joke_from_site()
    await broadcast(bot, f"😄 Смехуечка:\n\n{joke}")

async def check_changes(bot: Bot):
    schedule = parse_schedule()
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            old = json.load(f)
    else:
        old = {}
    with open(CACHE_FILE, "w") as f:
        json.dump(schedule, f, ensure_ascii=False)
    if old and old != schedule:
        await broadcast(bot, "⚠️ Расписание изменилось! Проверь /today")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users.add(update.effective_chat.id)
    save_users(users)
    keyboard = [[InlineKeyboardButton("📅 Расписание на сегодня", callback_data="today")]]
    await update.message.reply_text(
        "✅ Ты подписан! Буду присылать расписание каждый день в 7:00.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users.discard(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text("❌ Ты отписан от рассылки.")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rate_limited(update.effective_chat.id):
        await update.message.reply_text("⏳ Подожди 30 секунд перед следующим запросом.")
        return
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        await update.message.reply_text("Сегодня выходной 🎉")
        return
    await update.message.reply_text(build_message(day, lessons))
    joke = get_joke_from_site()
    await update.message.reply_text(f"😄 Смехуечка:\n\n{joke}")


async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rate_limited(update.effective_chat.id):
        await update.message.reply_text("⏳ Подожди 30 секунд перед следующим запросом.")
        return
    schedule = parse_schedule()
    day, lessons = get_tomorrow_lessons(schedule)
    if day is None:
        await update.message.reply_text("Завтра пар нет 🎉")
        return
    await update.message.reply_text(build_message(day, lessons, empty_text="Завтра пар нет 🎉"))

async def button_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if is_rate_limited(query.from_user.id):
        await query.answer("⏳ Подожди 30 секунд.", show_alert=True)
        return
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        await query.edit_message_text("Сегодня выходной 🎉")
        return
    await query.edit_message_text(build_message(day, lessons))

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CallbackQueryHandler(button_today, pattern="^today$"))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_daily_schedule, "cron", hour=7, minute=0, args=[app.bot])
    scheduler.add_job(check_changes, "interval", minutes=30, args=[app.bot])
    scheduler.start()

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()