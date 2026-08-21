import logging
import os
import sqlite3
import datetime as datetime_module
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram.ext import ContextTypes

import db

load_dotenv()

logger = logging.getLogger(__name__)

MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TIMEZONE = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")
REMINDER_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

TRIGGER_GOAL_DEADLINE = "goal_deadline_approaching"
TRIGGER_STALE_GOAL = "stale_active_goal"
CHECK_IN_TOPIC = "goal"
DAILY_CHECK_IN_BUDGET = 2
GLOBAL_CHECK_IN_COOLDOWN = timedelta(hours=3)
DEADLINE_WINDOW = timedelta(hours=24)
DEADLINE_COOLDOWN = timedelta(hours=48)
STALE_THRESHOLD = timedelta(days=5)
STALE_COOLDOWN = timedelta(days=5)
STALE_TARGET_DEAD_ZONE = timedelta(hours=48)


def _parse_reminder_datetime(value: object) -> datetime:
    """Parse a database reminder time and normalize it to the project timezone."""
    if isinstance(value, datetime_module.datetime):
        reminder_time = value
    elif isinstance(value, str):
        try:
            reminder_time = datetime_module.datetime.strptime(value, REMINDER_DATETIME_FORMAT)
        except ValueError:
            # Keep the database format as the primary path, while accepting a
            # timezone-aware datetime if one is returned by a compatible DB
            # adapter or existing data.
            reminder_time = datetime_module.datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError(f"unsupported remind_at value: {value!r}")

    if reminder_time.tzinfo is None:
        # SQLite stores the project's local wall-clock time without an offset.
        return reminder_time.replace(tzinfo=TIMEZONE)

    return reminder_time.astimezone(TIMEZONE)


def _parse_utc_datetime(value: object) -> datetime:
    """Parse a UTC database timestamp string into an aware UTC datetime."""
    if isinstance(value, datetime_module.datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime_module.datetime.strptime(value, REMINDER_DATETIME_FORMAT)
    else:
        raise ValueError(f"unsupported UTC timestamp value: {value!r}")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _utc_cutoff(now_utc: datetime, delta: timedelta) -> str:
    return (now_utc - delta).strftime(REMINDER_DATETIME_FORMAT)


def _is_quiet_hours(now_local: datetime) -> bool:
    hour = now_local.hour
    return hour >= 23 or hour < 8


def _goal_last_activity_utc(goal: sqlite3.Row) -> datetime | None:
    reference = goal["last_checked_in"] or goal["created_at"]
    if not reference:
        return None
    return _parse_utc_datetime(reference)


def _per_goal_cooldown_clear(
    last_checked_in: str | None,
    now_utc: datetime,
    cooldown: timedelta,
) -> bool:
    if last_checked_in is None:
        return True
    last_checked = _parse_utc_datetime(last_checked_in)
    return now_utc - last_checked >= cooldown


def _goal_target_datetime(goal: sqlite3.Row) -> datetime | None:
    target_date = goal["target_date"]
    if not target_date:
        return None
    try:
        return _parse_reminder_datetime(target_date)
    except (TypeError, ValueError):
        logger.exception("Invalid target_date for goal %s", goal["id"])
        return None


def _deadline_candidate(goal: sqlite3.Row, now_local: datetime, now_utc: datetime) -> datetime | None:
    target = _goal_target_datetime(goal)
    if target is None:
        return None

    time_until_target = target - now_local
    if time_until_target <= timedelta(0) or time_until_target > DEADLINE_WINDOW:
        return None
    if not _per_goal_cooldown_clear(goal["last_checked_in"], now_utc, DEADLINE_COOLDOWN):
        return None
    return target


def _stale_candidate(goal: sqlite3.Row, now_local: datetime, now_utc: datetime) -> datetime | None:
    if _deadline_candidate(goal, now_local, now_utc) is not None:
        return None

    target = _goal_target_datetime(goal)
    if target is not None:
        time_until_target = target - now_local
        if timedelta(0) < time_until_target <= STALE_TARGET_DEAD_ZONE:
            return None

    last_activity = _goal_last_activity_utc(goal)
    if last_activity is None or now_utc - last_activity < STALE_THRESHOLD:
        return None
    if not _per_goal_cooldown_clear(goal["last_checked_in"], now_utc, STALE_COOLDOWN):
        return None
    return last_activity


def _deadline_message(content: str) -> str:
    return f'Your goal "{content}" is due soon.'


def _stale_message(content: str) -> str:
    return f'Checking in on your goal "{content}".'


def _select_check_in_candidate(
    goals: list,
    now_local: datetime,
    now_utc: datetime,
) -> tuple[sqlite3.Row, str, str] | None:
    deadline_goals: list[tuple[datetime, sqlite3.Row]] = []
    stale_goals: list[tuple[datetime, sqlite3.Row]] = []

    for goal in goals:
        deadline_target = _deadline_candidate(goal, now_local, now_utc)
        if deadline_target is not None:
            deadline_goals.append((deadline_target, goal))
            continue

        stale_activity = _stale_candidate(goal, now_local, now_utc)
        if stale_activity is not None:
            stale_goals.append((stale_activity, goal))

    if deadline_goals:
        _, goal = min(deadline_goals, key=lambda item: item[0])
        return goal, TRIGGER_GOAL_DEADLINE, _deadline_message(goal["content"])

    if stale_goals:
        _, goal = min(stale_goals, key=lambda item: item[0])
        return goal, TRIGGER_STALE_GOAL, _stale_message(goal["content"])

    return None


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


async def check_proactive_triggers(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Evaluate proactive goal check-in triggers and deliver at most one message."""
    if not MY_CHAT_ID:
        logger.error("MY_CHAT_ID is not configured; proactive check-ins cannot be dispatched")
        return

    now_local = datetime.now(TIMEZONE)
    if _is_quiet_hours(now_local):
        return

    now_utc = now_local.astimezone(UTC)
    since_24h = _utc_cutoff(now_utc, timedelta(hours=24))
    since_3h = _utc_cutoff(now_utc, GLOBAL_CHECK_IN_COOLDOWN)

    try:
        recent_24h = db.get_recent_check_ins(since_24h)
        recent_3h = db.get_recent_check_ins(since_3h)
        goals = db.get_active_goals()
    except Exception:
        logger.exception("Scheduler failed to fetch proactive check-in state")
        return

    if len(recent_24h) >= DAILY_CHECK_IN_BUDGET:
        return
    if recent_3h:
        return

    candidate = _select_check_in_candidate(goals, now_local, now_utc)
    if candidate is None:
        return

    goal, triggered_by, message_text = candidate
    goal_id = goal["id"]

    try:
        booking = db.book_goal_check_in(goal_id, CHECK_IN_TOPIC, triggered_by)
    except Exception:
        logger.exception(
            "Failed to book proactive check-in for goal %s; skipping delivery",
            goal_id,
        )
        return

    try:
        await context.bot.send_message(
            chat_id=MY_CHAT_ID,
            text=message_text,
        )
    except Exception:
        logger.exception(
            "Failed to deliver proactive check-in for goal %s; rolling back booking",
            goal_id,
        )
        try:
            db.compensate_goal_check_in(
                booking["check_in_id"],
                goal_id,
                booking["previous_last_checked_in"],
            )
        except Exception:
            logger.exception(
                "Failed to roll back proactive check-in booking for goal %s",
                goal_id,
            )
        return

    logger.info(
        "Proactive check-in delivered for goal %s (%s)",
        goal_id,
        triggered_by,
    )
