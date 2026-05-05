"""
Database layer: SQLite with aiosqlite.
Tables: reminders, user_timezones.
All functions are async. All SQL uses parameterized queries.
"""
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger(__name__)

CREATE_REMINDERS_TABLE = """
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    remind_at TEXT NOT NULL,
    text TEXT NOT NULL,
    raw_transcript TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    is_sent INTEGER DEFAULT 0
);
"""

CREATE_USER_TIMEZONES_TABLE = """
CREATE TABLE IF NOT EXISTS user_timezones (
    user_id INTEGER PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    updated_at TEXT NOT NULL
);
"""

CREATE_IDX_USER = "CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id);"
CREATE_IDX_TIME = "CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders(remind_at, is_sent);"


async def init_db(db_path: str) -> None:
    """Create tables and indexes if they don't exist."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_REMINDERS_TABLE)
        await db.execute(CREATE_USER_TIMEZONES_TABLE)
        await db.execute(CREATE_IDX_USER)
        await db.execute(CREATE_IDX_TIME)
        await db.commit()
    logger.info("Database initialized at %s", db_path)


async def add_reminder(
    db_path: str,
    user_id: int,
    chat_id: int,
    remind_at: datetime,
    text: str,
    raw: str = "",
) -> int:
    """Insert a new reminder. Returns the new reminder ID."""
    now_iso = datetime.now(timezone.utc).isoformat()
    remind_iso = remind_at.isoformat()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO reminders (user_id, chat_id, remind_at, text, raw_transcript, created_at, is_sent)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (user_id, chat_id, remind_iso, text, raw, now_iso),
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminders(db_path: str) -> list[dict]:
    """Return all unsent reminders ordered by remind_at."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reminders WHERE is_sent = 0 ORDER BY remind_at"
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def mark_sent(db_path: str, reminder_id: int) -> None:
    """Mark a reminder as sent."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE reminders SET is_sent = 1 WHERE id = ?",
            (reminder_id,),
        )
        await db.commit()


async def get_user_reminders(db_path: str, user_id: int) -> list[dict]:
    """Return all pending (unsent) reminders for a specific user."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM reminders WHERE user_id = ? AND is_sent = 0 ORDER BY remind_at",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def delete_reminder(db_path: str, reminder_id: int, user_id: int) -> bool:
    """Delete a reminder by ID (only if it belongs to the user). Returns True if deleted."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "DELETE FROM reminders WHERE id = ? AND user_id = ? AND is_sent = 0",
            (reminder_id, user_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def set_user_timezone(db_path: str, user_id: int, timezone_name: str) -> None:
    """Insert or update user timezone."""
    now_iso = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO user_timezones (user_id, timezone, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET timezone = excluded.timezone, updated_at = excluded.updated_at
            """,
            (user_id, timezone_name, now_iso),
        )
        await db.commit()


async def get_user_timezone(db_path: str, user_id: int) -> str:
    """Get user's timezone string, default 'UTC'."""
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            "SELECT timezone FROM user_timezones WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else "UTC"
