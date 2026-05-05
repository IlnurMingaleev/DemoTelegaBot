"""
Reminder scheduler using APScheduler AsyncIOScheduler.
Manages job scheduling, firing, and cleanup.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import pytz

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=pytz.utc)


def start_scheduler() -> None:
    """Start the APScheduler. Call once at bot startup."""
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler() -> None:
    """Stop the APScheduler gracefully. Call on bot shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


def schedule_reminder(
    bot,
    reminder_id: int,
    chat_id: int,
    text: str,
    remind_at: datetime,
    db_path: str,
) -> None:
    """
    Schedule a reminder job in APScheduler.
    If the job already exists (e.g. after restart), it will be replaced.
    """
    job_id = f"reminder_{reminder_id}"
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=remind_at),
        args=[bot, reminder_id, chat_id, text, db_path],
        id=job_id,
        replace_existing=True,
        misfire_grace_time=300,  # fire up to 5 min late if bot was briefly offline
    )
    logger.info(
        "Scheduled reminder #%d for chat %d at %s",
        reminder_id, chat_id, remind_at.isoformat(),
    )


def cancel_reminder(reminder_id: int) -> None:
    """Remove a scheduled reminder job. Safe to call even if job doesn't exist."""
    job_id = f"reminder_{reminder_id}"
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
        logger.info("Cancelled reminder #%d", reminder_id)


async def send_reminder(
    bot,
    reminder_id: int,
    chat_id: int,
    text: str,
    db_path: str,
) -> None:
    """
    Fire a reminder: send message to user, mark as sent in DB.
    Called by APScheduler at the scheduled time.
    """
    try:
        await bot.send_message(
            chat_id,
            f"🔔 <b>Напоминание!</b>\n\n{text}",
        )
        logger.info("Sent reminder #%d to chat %d", reminder_id, chat_id)
    except Exception as e:
        logger.error("Failed to send reminder #%d to chat %d: %s", reminder_id, chat_id, e)
    finally:
        # Always mark as sent to avoid re-firing
        try:
            from bot.database.models import mark_sent
            await mark_sent(db_path, reminder_id)
        except Exception as e:
            logger.error("Failed to mark reminder #%d as sent: %s", reminder_id, e)


async def load_pending_reminders(bot, db_path: str) -> None:
    """
    Load all pending reminders from DB and reschedule them.
    Called at bot startup to restore reminders after restart.
    """
    from bot.database.models import get_pending_reminders
    from datetime import timezone as dt_timezone

    try:
        reminders = await get_pending_reminders(db_path)
        now = datetime.now(dt_timezone.utc)
        loaded = 0
        skipped = 0

        for r in reminders:
            try:
                remind_at = datetime.fromisoformat(r["remind_at"])
                if remind_at.tzinfo is None:
                    remind_at = pytz.utc.localize(remind_at)

                if remind_at <= now:
                    # Overdue reminder — fire immediately
                    logger.info(
                        "Firing overdue reminder #%d (was due %s)",
                        r["id"], remind_at.isoformat(),
                    )
                    await send_reminder(bot, r["id"], r["chat_id"], r["text"], db_path)
                    skipped += 1
                else:
                    schedule_reminder(
                        bot=bot,
                        reminder_id=r["id"],
                        chat_id=r["chat_id"],
                        text=r["text"],
                        remind_at=remind_at,
                        db_path=db_path,
                    )
                    loaded += 1
            except Exception as e:
                logger.error("Failed to reschedule reminder #%d: %s", r["id"], e)

        logger.info(
            "Loaded %d pending reminders (%d overdue fired) from DB",
            loaded, skipped,
        )
    except Exception as e:
        logger.error("Failed to load pending reminders: %s", e)
