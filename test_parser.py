from datetime import datetime
from pathlib import Path
import unittest

from bot import BASE_DIR, CACHE_FILE, USERS_FILE, get_lessons_for_date
from schedule_parser import parse_day_label


class BotScheduleTests(unittest.TestCase):
    def test_get_lessons_for_date_matches_full_date(self):
        schedule = {
            "2026-01-29": {"label": "Срд,29 января", "lessons": {"1": {"name": "January lesson"}}},
            "2026-04-29": {"label": "Срд,29 апреля", "lessons": {"1": {"name": "April lesson"}}},
        }

        day, lessons = get_lessons_for_date(schedule, datetime(2026, 4, 29))

        self.assertEqual(day, "Срд,29 апреля")
        self.assertEqual(lessons["1"]["name"], "April lesson")

    def test_parse_day_label_parses_russian_months(self):
        parsed = parse_day_label("Срд,29 апреля", current_year=2026)

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.isoformat(), "2026-04-29")

    def test_data_files_are_anchored_to_project_directory(self):
        self.assertEqual(USERS_FILE, BASE_DIR / "users.json")
        self.assertEqual(CACHE_FILE, BASE_DIR / "cache.json")
        self.assertEqual(USERS_FILE.parent, Path(BASE_DIR))


if __name__ == "__main__":
    unittest.main()
