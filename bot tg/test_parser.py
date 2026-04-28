import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from schedule_parser import parse_schedule, format_lesson  # не parser!
from bot import send_daily_schedule

load_dotenv()

bot = Bot(token=os.getenv("TOKEN"))
asyncio.run(send_daily_schedule(bot))
schedule = parse_schedule()

for day, lessons in list(schedule.items())[:5]:
    print(f"\n{'='*40}")
    print(f"  {day}")
    print('='*40)
    if lessons:
        for num, lesson in sorted(lessons.items()):
            print(format_lesson(num, lesson))
            print()
    else:
        print("  Пар нет")

# 2. Тест отправки в телеграм
print("\n=== ТЕСТ ОТПРАВКИ ===")
bot = Bot(token=os.getenv("TOKEN"))
asyncio.run(send_daily_schedule(bot))