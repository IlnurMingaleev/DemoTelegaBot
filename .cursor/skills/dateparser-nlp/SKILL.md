---
name: dateparser-nlp
description: Extract datetime from Russian natural language using dateparser + pytz. Use when implementing date/time parsing from transcribed voice or text reminders. Covers relative dates, absolute dates, timezone-aware results, and fallback handling.
disable-model-invocation: true
---

# dateparser NLP — Russian Datetime Extraction

## Installation

```
dateparser>=1.2.0
pytz>=2024.1
```

## Core extraction function

```python
import dateparser
from datetime import datetime
import pytz

def parse_reminder_datetime(text: str, user_timezone: str = "UTC") -> datetime | None:
    """
    Parse datetime from Russian text in user's timezone.
    Returns timezone-aware datetime or None if not found.

    Examples:
      "завтра в 15:00" → tomorrow 15:00 in user_tz
      "через 2 часа напомни про встречу" → now + 2h
      "15 мая в 10 утра" → May 15 10:00
      "в пятницу вечером" → next Friday ~18:00
    """
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)

    settings = {
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "TIMEZONE": user_timezone,
        "TO_TIMEZONE": user_timezone,
        "PREFER_DAY_OF_MONTH": "first",
        "DATE_ORDER": "DMY",
        "RELATIVE_BASE": now,
    }

    result = dateparser.parse(text, languages=["ru", "en"], settings=settings)
    if result and result > now:
        return result
    return None
```

## Extracting reminder text (strip date/time words)

```python
import re

DATE_PATTERNS = [
    r"(завтра|послезавтра|сегодня|в понедельник|во вторник|в среду|в четверг|в пятницу|в субботу|в воскресенье)",
    r"через\s+\d+\s+(минут[у]?|час[а|ов]?|дн[ей|я]?)",
    r"\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)",
    r"в\s+\d{1,2}[:.]\d{2}",
    r"в\s+\d{1,2}\s+(утра|дня|вечера|ночи)",
    r"напомни(те)?(\s+мне)?",
    r"поставь\s+напоминание",
    r"напоминание",
]

def extract_reminder_text(text: str) -> str:
    """Remove date/time words to get the reminder subject."""
    cleaned = text
    for pattern in DATE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", cleaned).strip(" —-–")
```

## Timezone FSM flow

User sets timezone once via `/timezone` command:

```python
# FSM state
class TimezoneState(StatesGroup):
    waiting_for_tz = State()

# Store in DB: INSERT OR REPLACE INTO user_timezones (user_id, timezone) VALUES (?, ?)
# Retrieve: SELECT timezone FROM user_timezones WHERE user_id = ?
# Default: "UTC"
```

Timezone list for inline keyboard (most common for RU users):
```python
COMMON_TIMEZONES = [
    ("🇷🇺 Москва (UTC+3)", "Europe/Moscow"),
    ("🇷🇺 Екатеринбург (UTC+5)", "Asia/Yekaterinburg"),
    ("🇷🇺 Новосибирск (UTC+7)", "Asia/Novosibirsk"),
    ("🇷🇺 Владивосток (UTC+10)", "Asia/Vladivostok"),
    ("🇺🇦 Киев (UTC+2/3)", "Europe/Kiev"),
    ("🇰🇿 Алматы (UTC+5)", "Asia/Almaty"),
    ("🌍 UTC", "UTC"),
]
```

## Confirmation message format

```python
def format_confirmation(dt: datetime, text: str, timezone: str) -> str:
    tz = pytz.timezone(timezone)
    local_dt = dt.astimezone(tz)
    offset = local_dt.strftime("%z")
    offset_str = f"UTC{offset[:3]}:{offset[3:]}" if len(offset) == 5 else f"UTC{offset}"
    return (
        f"✅ Напоминание установлено!\n"
        f"📅 Дата: {local_dt.strftime('%d %B %Y')}\n"
        f"🕒 Время: {local_dt.strftime('%H:%M')}\n"
        f"🌍 Часовой пояс: {timezone} ({offset_str})\n"
        f"📝 Текст: {text}"
    )
```

## Fallback — ask user to clarify

```python
if parsed_dt is None:
    await message.answer(
        "❓ Не смог найти дату/время в сообщении.\n"
        "Попробуйте: «завтра в 15:00», «через 2 часа», «15 мая в 10 утра»"
    )
    return
```
