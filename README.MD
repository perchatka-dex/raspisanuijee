# Бот расписания для колледжа

Хобби-проект — Telegram-бот для просмотра расписания занятий в колледже.

## Возможности

- Расписание на сегодня, завтра и текущую неделю
- Ежедневная рассылка в 7:00 по московскому времени
- Беззвучные уведомления по выходным
- Оповещение при изменении расписания

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Подписаться на рассылку |
| `/stop` | Отписаться от рассылки |
| `/today` | Расписание на сегодня |
| `/tomorrow` | Расписание на завтра |
| `/week` | Расписание на неделю |

## Запуск

```bash
cp .env.example .env
# заполни TOKEN в .env
docker compose up -d
```

---

# College Schedule Bot

A hobby project — a Telegram bot for viewing class schedules at college.

## Features

- Schedule for today, tomorrow, and the current week
- Daily broadcast at 7:00 AM Moscow time
- Silent notifications on weekends
- Notifications when the schedule changes

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to daily updates |
| `/stop` | Unsubscribe |
| `/today` | Today's schedule |
| `/tomorrow` | Tomorrow's schedule |
| `/week` | This week's schedule |

## Running

```bash
cp .env.example .env
# fill in TOKEN in .env
docker compose up -d
```
