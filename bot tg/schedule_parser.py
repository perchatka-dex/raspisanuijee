import requests
from bs4 import BeautifulSoup
import re
import json

URL = "https://conference.aumsu.ru/rasp/OCHNOE/HTML/143.html"

TIMES = {
    "1": "09:00–10:30",
    "2": "10:40–12:10",
    "3": "12:20–13:50",
    "4": "14:30–16:00",
    "5": "16:10–17:40",
    "6": "17:50–19:20",
}

def fetch_html():
    r = requests.get(URL, timeout=10)
    r.encoding = "windows-1251"  # сайт в этой кодировке [1]
    return r.text

def parse_lesson_text(text):
    """
    Парсит строку пары. Форматы из реального расписания [1]:
    - 'л.Компьютерные сети Мельниченко А.Д. У-405'
    - 'лаб.Управление и автоматизация баз данных 1 п/г Святецкая О.М. У-418А 2 п/г Джингалиева М.В. У-418'
    - 'экз.Элементы высшей математики Губарева М.А. 4-315'
    """
    text = text.strip()
    if not text or text == "_":
        return None

    lesson = {}

    # тип пары
    type_match = re.match(r'^(лаб|пр|л|экз)\.', text)
    if type_match:
        type_map = {
            "лаб": "Лабораторная",
            "пр": "Практика",
            "л": "Лекция",
            "экз": "Экзамен"
        }
        lesson["type"] = type_map.get(type_match.group(1), "")
        text = text[type_match.end():]
    else:
        lesson["type"] = ""

    # проверяем подгруппы — паттерн "1 п/г ... каб 2 п/г ... каб" [1]
    sg = re.search(
        r'^(.+?)\s+1\s*п/г\s+(.+?)\s+([\w\-]+)\s+2\s*п/г\s+(.+?)\s+([\w\-]+)\s*$',
        text
    )
    if sg:
        lesson["name"] = sg.group(1).strip()
        lesson["subgroups"] = {
            "1": {"teacher": sg.group(2).strip(), "room": sg.group(3).strip()},
            "2": {"teacher": sg.group(4).strip(), "room": sg.group(5).strip()}
        }
        return lesson

    # обычная пара — ищем "Фамилия И.О." перед кабинетом
    teacher_match = re.search(r'(.+?)\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)\s+([\w\-]+)\s*$', text)
    if teacher_match:
        lesson["name"] = teacher_match.group(1).strip()
        lesson["teacher"] = teacher_match.group(2).strip()
        lesson["room"] = teacher_match.group(3).strip()
    else:
        lesson["name"] = text
        lesson["teacher"] = ""
        lesson["room"] = ""

    return lesson

def parse_schedule():
    html = fetch_html()
    soup = BeautifulSoup(html, "html.parser")
    schedule = {}

    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        # заголовок — номера пар
        headers = [td.get_text(strip=True) for td in rows[0].find_all(["td", "th"])]
        pair_indices = {}
        for i, h in enumerate(headers):
            m = re.match(r'^(\d+)', h)
            if m:
                pair_indices[i] = m.group(1)

        if not pair_indices:
            continue

        # строки с днями
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            texts = [c.get_text(separator=" ", strip=True) for c in cells]
            if not texts:
                continue

            # первая ячейка — день вида "Пнд,23 февраля"
            day_text = texts[0]
            if not re.match(r'^(Пнд|Втр|Срд|Чтв|Птн|Сбт)', day_text):
                continue

            schedule[day_text] = {}
            for col_idx, pair_num in pair_indices.items():
                if col_idx < len(texts):
                    lesson = parse_lesson_text(texts[col_idx])
                    if lesson:
                        schedule[day_text][pair_num] = lesson

    return schedule

def format_lesson(pair_num, lesson):
    time = TIMES.get(pair_num, f"{pair_num}-я пара")
    lesson_type = lesson.get("type", "")
    name = lesson.get("name", "")
    title = f"{name} ({lesson_type})" if lesson_type else name

    lines = [f"№{pair_num} · {time}"]

    if lesson.get("subgroups"):
        sg = lesson["subgroups"]
        rooms = f"{sg['1']['room']} / {sg['2']['room']}"
        lines.append(f"🏫 {rooms}")
        lines.append(title)
        lines.append(f"👥 1 п/г: {sg['1']['teacher']} | 2 п/г: {sg['2']['teacher']}")
    else:
        if lesson.get("room"):
            lines.append(f"🏫 {lesson['room']}")
        lines.append(title)
        if lesson.get("teacher"):
            lines.append(f"👤 {lesson['teacher']}")

    return "\n".join(lines)
