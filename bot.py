import json
import os
from datetime import datetime, timedelta, time as dtime
from pathlib import Path

from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from schedule_parser import parse_schedule, format_lesson

load_dotenv()
TOKEN = os.getenv("TOKEN")
BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"
CACHE_FILE = BASE_DIR / "cache.json"

SCHEDULE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⚪ Сегодня", callback_data="today"),
        InlineKeyboardButton("🔵 Завтра", callback_data="tomorrow"),
        InlineKeyboardButton("🔴 Неделя", callback_data="week"),
    ]
])

last_request = {}
COOLDOWN = 3

def is_rate_limited(chat_id: int) -> bool:
    now = datetime.now()
    if chat_id in last_request:
        if now - last_request[chat_id] < timedelta(seconds=COOLDOWN):
            return True
    last_request[chat_id] = now
    return False

def load_users():
    if USERS_FILE.exists():
        with USERS_FILE.open(encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(list(users), f)

def get_lessons_for_date(schedule, target_date):
    target_key = target_date.date().isoformat()
    day_schedule = schedule.get(target_key)
    if not day_schedule:
        return None, {}
    return day_schedule["label"], day_schedule["lessons"]

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

def build_week_message(schedule):
    today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    monday = today - timedelta(days=today.weekday())
    messages = []
    for i in range(6):  # Пн–Сб
        day_date = monday + timedelta(days=i)
        key = day_date.isoformat()
        day_schedule = schedule.get(key)
        if day_schedule:
            messages.append(build_message(day_schedule["label"], day_schedule["lessons"]))
    return messages

async def broadcast(bot: Bot, message: str, reply_markup=None):
    users = load_users()
    print(f"Рассылка для {len(users)} пользователей")
    for chat_id in users:
        try:
            await bot.send_message(chat_id, message, reply_markup=reply_markup)
        except Exception as e:
            print(f"Ошибка {chat_id}: {e}")

async def send_daily_schedule(context: ContextTypes.DEFAULT_TYPE):
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        return
    await broadcast(context.bot, build_message(day, lessons), reply_markup=SCHEDULE_KEYBOARD)

async def check_changes(context: ContextTypes.DEFAULT_TYPE):
    schedule = parse_schedule()
    if CACHE_FILE.exists():
        with CACHE_FILE.open(encoding="utf-8") as f:
            old = json.load(f)
    else:
        old = {}
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False)
    if old and old != schedule:
        await broadcast(context.bot, "⚠️ Расписание изменилось! Проверь /today")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users.add(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text(
        "✅ Ты подписан! Буду присылать расписание каждый день в 7:00.",
        reply_markup=SCHEDULE_KEYBOARD
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    users.discard(update.effective_chat.id)
    save_users(users)
    await update.message.reply_text("❌ Ты отписан от рассылки.")

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rate_limited(update.effective_chat.id):
        await update.message.reply_text("⏳ Подожди 3 секунды перед следующим запросом.")
        return
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        await update.message.reply_text("Сегодня выходной 🎉", reply_markup=SCHEDULE_KEYBOARD)
        return
    msg = await update.message.reply_text(build_message(day, lessons), reply_markup=SCHEDULE_KEYBOARD)

async def tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rate_limited(update.effective_chat.id):
        await update.message.reply_text("⏳ Подожди 3 секунды перед следующим запросом.")
        return
    schedule = parse_schedule()
    day, lessons = get_tomorrow_lessons(schedule)
    if day is None:
        await update.message.reply_text("Завтра пар нет 🎉", reply_markup=SCHEDULE_KEYBOARD)
        return
    msg = await update.message.reply_text(
        build_message(day, lessons, empty_text="Завтра пар нет 🎉"),
        reply_markup=SCHEDULE_KEYBOARD
    )

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_rate_limited(update.effective_chat.id):
        await update.message.reply_text("⏳ Подожди 3 секунды перед следующим запросом.")
        return
    schedule = parse_schedule()
    messages = build_week_message(schedule)
    if not messages:
        await update.message.reply_text("На этой неделе пар нет 🎉", reply_markup=SCHEDULE_KEYBOARD)
        return
    msg = await update.message.reply_text(
        "\n\n─────────────────\n\n".join(messages),
        reply_markup=SCHEDULE_KEYBOARD
    )

async def button_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    schedule = parse_schedule()
    day, lessons = get_today_lessons(schedule)
    if day is None:
        await query.edit_message_text("Сегодня выходной 🎉", reply_markup=SCHEDULE_KEYBOARD)
    else:
        await query.edit_message_text(build_message(day, lessons), reply_markup=SCHEDULE_KEYBOARD)

async def button_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    schedule = parse_schedule()
    day, lessons = get_tomorrow_lessons(schedule)
    if day is None:
        await query.edit_message_text("Завтра пар нет 🎉", reply_markup=SCHEDULE_KEYBOARD)
    else:
        await query.edit_message_text(
            build_message(day, lessons, empty_text="Завтра пар нет 🎉"),
            reply_markup=SCHEDULE_KEYBOARD
        )

async def button_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    schedule = parse_schedule()
    messages = build_week_message(schedule)
    if not messages:
        await query.edit_message_text("На этой неделе пар нет 🎉", reply_markup=SCHEDULE_KEYBOARD)
    else:
        await query.edit_message_text(
            "\n\n─────────────────\n\n".join(messages),
            reply_markup=SCHEDULE_KEYBOARD
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("tomorrow", tomorrow))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(CallbackQueryHandler(button_today, pattern="^today$"))
    app.add_handler(CallbackQueryHandler(button_tomorrow, pattern="^tomorrow$"))
    app.add_handler(CallbackQueryHandler(button_week, pattern="^week$"))

    job_queue = app.job_queue
    tz = ZoneInfo("Europe/Moscow")
    job_queue.run_daily(send_daily_schedule, time=dtime(7, 0, tzinfo=tz))
    job_queue.run_repeating(check_changes, interval=1800, first=10)

    print("✅ Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
