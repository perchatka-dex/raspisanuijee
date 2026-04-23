import asyncio
import json
import os
import re
from datetime import datetime

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

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

def get_today_lessons(schedule):
    today = datetime.now()
    abbr = WEEKDAYS_RU.get(today.weekday())
    if not abbr:
        return None, {}
    for key, lessons in schedule.items():
        if key.startswith(abbr):
            date_match = re.search(r'(\d+)', key)
            if date_match and int(date_match.group(1)) == today.day:
                return key, lessons
    return None, {}

def build_message(day, lessons):
    if not lessons:
        return f"📅 {day}\n\nСегодня пар нет 🎉"
    lines = [f"📅 {day}\n"]
    for num, lesson in sorted(lessons.items()):
        lines.append(format_lesson(num, lesson))
    return "\n".join(lines)

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
        "✅ Ты подписан! Буду присылать расписание каждый день в 8:00.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users.discard(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text("❌ Ты отписан от рассылки.")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        await update.message.reply_text("Сегодня выходной 🎉")
        return
    await update.message.reply_text(build_message(day, lessons))
async def button_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
    app.add_handler(CallbackQueryHandler(button_today, pattern="^today$"))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_daily_schedule, "cron", hour=8, minute=0, args=[app.bot])
    scheduler.add_job(check_changes, "interval", minutes=30, args=[app.bot])
    scheduler.start()

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()