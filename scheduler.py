import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram.ext import ContextTypes

import db

load_dotenv()

logger = logging.getLogger(__name__)

MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TIMEZONE = ZoneInfo("Asia/Kolkata")
REMINDER_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_reminder_datetime(value: object) -> datetime:
    """Parse a database reminder time and normalize it to the project timezone."""
    if isinstance(value, datetime):
        reminder_time = value
    elif isinstance(value, str):
        try:
            reminder_time = datetime.strptime(value, REMINDER_DATETIME_FORMAT)
        except ValueError:
            # Keep the database format as the primary path, while accepting a
            # timezone-aware datetime if one is returned by a compatible DB
            # adapter or existing data.
            reminder_time = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError(f"unsupported remind_at value: {value!r}")

    if reminder_time.tzinfo is None:
        # SQLite stores the project's local wall-clock time without an offset.
        return reminder_time.replace(tzinfo=TIMEZONE)

    return reminder_time.astimezone(TIMEZONE)


async def check_due_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send pending reminders whose stored local time has arrived."""
    try:
        pending_reminders = db.get_pending_reminders()
    except Exception:
        logger.exception("Scheduler failed to fetch pending reminders")
        return

    if not MY_CHAT_ID:
        logger.error("MY_CHAT_ID is not configured; reminders cannot be dispatched")
        return

    now = datetime.now(TIMEZONE)

    for reminder in pending_reminders:
        reminder_id = reminder["id"]
        content = reminder["content"]

        try:
            remind_at = _parse_reminder_datetime(reminder["remind_at"])
        except (TypeError, ValueError):
            logger.exception(
                "Invalid remind_at for reminder %s; leaving it pending",
                reminder_id,
            )
            continue

        if now < remind_at:
            continue

        logger.info("Reminder %s is due; attempting delivery", reminder_id)
        # Plain text avoids depending on Telegram Markdown/HTML parse modes.
        message_text = f"Reminder:\n\n{content}"

        try:
            await context.bot.send_message(
                chat_id=MY_CHAT_ID,
                text=message_text,
            )
        except Exception:
            logger.exception(
                "Failed to deliver reminder %s; leaving it pending",
                reminder_id,
            )
            continue

        try:
            updated = db.update_reminder_status(reminder_id, "sent")
            if not updated:
                logger.error(
                    "Reminder %s was delivered, but marking it sent returned False",
                    reminder_id,
                )
            else:
                logger.info("Reminder %s delivered and marked sent", reminder_id)
        except Exception:
            logger.exception(
                "Reminder %s was delivered, but updating its status failed",
                reminder_id,
            )
