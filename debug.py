import requests
from bs4 import BeautifulSoup

URL = "https://conference.aumsu.ru/rasp/OCHNOE/HTML/143.html"

r = requests.get(URL, timeout=10)
r.encoding = "windows-1251"
soup = BeautifulSoup(r.text, "html.parser")

# смотрим первые 50 строк таблицы
table = soup.find("table")
if table:
    rows = table.find_all("tr")
    for row in rows[:20]:
        cells = row.find_all(["td", "th"])
        texts = [c.get_text(strip=True) for c in cells]
        print(texts)
else:
    print("Таблица не найдена")
    print(r.text[:2000])