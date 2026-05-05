"""
NLP service: extracts datetime and reminder text from Russian natural language.
Uses dateparser.search.search_dates() to find dates embedded inside phrases,
and pytz for timezone handling.
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime

import dateparser
import dateparser.search
import pytz

logger = logging.getLogger(__name__)

RUSSIAN_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

_DATE_STRIP_PATTERNS = [
    r"(напомни(те)?(\s+мне)?|поставь\s+напоминание|напоминание)\s*",
    r"через\s+\d+\s+(минут[у]?|час[аов]?|дн[ейя]?|недел[юи]?)\s*",
    r"(завтра|послезавтра|сегодня)\s*",
    r"в\s+(понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)\s*",
    r"\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)(\s+\d{4})?\s*",
    r"в\s+\d{1,2}[:.]\d{2}\s*",
    r"в\s+\d{1,2}\s+(утра|дня|вечера|ночи)\s*",
    r"\d{1,2}[:.]\d{2}\s*",
    r"(утром|вечером|ночью|днём|днем)\s*",
]


@dataclass
class ParsedReminder:
    remind_at: datetime
    text: str
    raw_transcript: str


def _make_settings(user_timezone: str, now_naive: datetime) -> dict:
    """Build dateparser settings dict with naive RELATIVE_BASE."""
    return {
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": False,   # get naive result, we localize manually
        "TIMEZONE": user_timezone,
        "DATE_ORDER": "DMY",
        "RELATIVE_BASE": now_naive,          # must be naive datetime
        "PREFER_DAY_OF_MONTH": "first",
    }


def _normalize_time_notation(text: str) -> str:
    """
    Normalize common speech-recognition time variants before parsing.
    e.g. "15.00" → "15:00", "пять утра" → handled by dateparser
    """
    # Convert "15.00" / "9.30" style (dot separator) to "15:00"
    text = re.sub(r"\b(\d{1,2})\.(\d{2})\b", r"\1:\2", text)
    return text


def parse_reminder_datetime(text: str, user_timezone: str = "UTC") -> datetime | None:
    """
    Extract a future datetime from Russian natural-language text.
    Tries search_dates() first (finds date inside a phrase),
    then falls back to full-text parse().
    Returns timezone-aware datetime or None.
    """
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning("Unknown timezone '%s', falling back to UTC", user_timezone)
        tz = pytz.utc

    now_aware = datetime.now(tz)
    now_naive = now_aware.replace(tzinfo=None)   # dateparser needs naive RELATIVE_BASE
    settings = _make_settings(user_timezone, now_naive)

    normalized = _normalize_time_notation(text)
    logger.info("NLP input (normalized): '%s'", normalized)

    # Strategy 1: search_dates — finds date expressions embedded in free text
    result_dt = _try_search_dates(normalized, settings)

    # Strategy 2: full-text dateparser.parse — works well for "tomorrow at 3pm" style
    if result_dt is None:
        result_dt = _try_parse(normalized, settings)

    if result_dt is None:
        logger.info("No datetime found in: '%s'", text)
        return None

    # Localize the naive result to user's timezone
    try:
        result_aware = tz.localize(result_dt)
    except Exception:
        result_aware = result_dt.replace(tzinfo=tz)

    # Must be in the future
    if result_aware <= now_aware:
        logger.info("Parsed datetime %s is in the past, ignoring", result_aware)
        return None

    logger.info("Parsed datetime: %s (tz=%s)", result_aware.isoformat(), user_timezone)
    return result_aware


def _try_search_dates(text: str, settings: dict) -> datetime | None:
    """Use dateparser.search.search_dates to find embedded date expressions."""
    try:
        results = dateparser.search.search_dates(
            text,
            languages=["ru", "en"],
            settings=settings,
        )
        if results:
            # Take the first found date
            _matched_str, dt = results[0]
            logger.debug("search_dates found: '%s' → %s", _matched_str, dt)
            return dt
    except Exception as e:
        logger.debug("search_dates failed: %s", e)
    return None


def _try_parse(text: str, settings: dict) -> datetime | None:
    """Use dateparser.parse as a fallback for the full text."""
    try:
        dt = dateparser.parse(text, languages=["ru", "en"], settings=settings)
        if dt:
            logger.debug("dateparser.parse found: %s", dt)
        return dt
    except Exception as e:
        logger.debug("dateparser.parse failed: %s", e)
    return None


def extract_reminder_text(text: str) -> str:
    """Remove date/time words from text to get the reminder subject."""
    cleaned = text
    for pattern in _DATE_STRIP_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[-–—]+", " ", cleaned)
    cleaned = re.sub(r"[.!?]+$", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 2 else text.strip()


def _offset_str(dt: datetime) -> str:
    offset = dt.strftime("%z")
    if len(offset) >= 5:
        sign = offset[0]
        hours = int(offset[1:3])
        minutes = int(offset[3:5])
        if minutes == 0:
            return f"UTC{sign}{hours}"
        return f"UTC{sign}{hours}:{minutes:02d}"
    return "UTC"


def format_confirmation(dt: datetime, text: str, timezone: str) -> str:
    """Format the reminder confirmation message in Russian."""
    try:
        tz = pytz.timezone(timezone)
    except Exception:
        tz = pytz.utc
    local_dt = dt.astimezone(tz)
    month_name = RUSSIAN_MONTHS.get(local_dt.month, str(local_dt.month))
    offset_str = _offset_str(local_dt)

    return (
        f"✅ <b>Напоминание установлено!</b>\n\n"
        f"📅 <b>Дата:</b> {local_dt.day} {month_name} {local_dt.year}\n"
        f"🕒 <b>Время:</b> {local_dt.strftime('%H:%M')}\n"
        f"🌍 <b>Часовой пояс:</b> {timezone} ({offset_str})\n"
        f"📝 <b>Текст:</b> {text}"
    )


async def get_user_timezone(user_id: int, db_path: str) -> str:
    """Get user's timezone from DB, default UTC."""
    try:
        import aiosqlite
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT timezone FROM user_timezones WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
        return row[0] if row else "UTC"
    except Exception as e:
        logger.error("Failed to get user timezone: %s", e)
        return "UTC"


async def process_reminder_text(
    text: str,
    user_id: int,
    db_path: str,
) -> "ParsedReminder | None":
    """
    Main entry point: parse text into a ParsedReminder.
    Returns None if no valid future datetime found.
    """
    user_tz = await get_user_timezone(user_id, db_path)
    remind_at = parse_reminder_datetime(text, user_tz)

    if remind_at is None:
        return None

    reminder_text = extract_reminder_text(text)
    if not reminder_text or len(reminder_text) < 2:
        reminder_text = text.strip()

    logger.info(
        "Reminder saved: user=%d at=%s tz=%s text='%s'",
        user_id, remind_at.isoformat(), user_tz, reminder_text,
    )

    return ParsedReminder(
        remind_at=remind_at,
        text=reminder_text,
        raw_transcript=text,
    )
