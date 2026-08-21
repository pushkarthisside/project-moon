import asyncio
import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from context import get_formatted_system_prompt
from db import init_db, log_message
from llm import get_reply, groq_client
from memory import process_turn_memory
from scheduler import check_due_reminders, check_proactive_triggers

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


_TELEGRAM_CODE_BLOCK = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
_TELEGRAM_BOLD = re.compile(
    r"\*\*([^\n]+?)\*\*|(?<!\w)__([^\n]+?)__(?!\w)"
)
_TELEGRAM_ITALIC = re.compile(
    r"(?<!\*)\*([^*\n]+?)\*(?!\*)|(?<![_\w])_([^_\n]+?)_(?![_\w])"
)


def _strip_telegram_emphasis(match: re.Match, source: str) -> str:
    """Remove one emphasis span without joining surrounding words."""
    content = match.group(1) or match.group(2)
    before = source[match.start() - 1] if match.start() else ""
    after = source[match.end()] if match.end() < len(source) else ""
    # Telegram's Markdown delimiters are removed before sending plain text.
    # If a delimiter was attached directly to neighboring text, retain a
    # separator so removing it cannot join two words (or a word and an
    # opening parenthesis) together.
    prefix = " " if before.isalnum() and content[0] not in " \t\r\n" else ""
    suffix = " " if after.isalnum() and content[-1] not in " \t\r\n" else ""
    return f"{prefix}{content}{suffix}"


def _plain_text_for_telegram(text: str) -> str:
    """Keep Telegram replies readable while avoiding Markdown parse hazards."""
    if not isinstance(text, str):
        return ""

    code_blocks = []

    def preserve_code_block(match: re.Match) -> str:
        code_blocks.append(match.group(0))
        return f"\x00CODE_BLOCK_{len(code_blocks) - 1}\x00"

    text = _TELEGRAM_CODE_BLOCK.sub(preserve_code_block, text)
    text = _TELEGRAM_BOLD.sub(
        lambda match: _strip_telegram_emphasis(match, text), text
    )
    text = _TELEGRAM_ITALIC.sub(
        lambda match: _strip_telegram_emphasis(match, text), text
    )

    for index, code_block in enumerate(code_blocks):
        text = text.replace(f"\x00CODE_BLOCK_{index}\x00", code_block)
    return text


def _needs_active_goal_context(user_text: str) -> bool:
    """Return whether the current message explicitly needs active goals."""
    normalized = " ".join(user_text.casefold().split())

    view_phrases = (
        "active goals",
        "my goals",
        "which goals",
        "what goals",
        "goal should",
        "review my objectives",
    )
    if any(phrase in normalized for phrase in view_phrases):
        return True

    has_goal_reference = re.search(r"\bgoal(?:s)?\b", normalized) is not None
    if not has_goal_reference:
        return False

    creation_request = re.search(r"\b(create|add|set)\s+(?:a\s+)?goal\b", normalized)
    if creation_request:
        return False

    completion_words = ("mark", "complete", "completed", "finish", "finished", "done")
    removal_words = ("remove", "delete", "drop", "cancel", "abandon")
    if any(word in normalized for word in completion_words + removal_words):
        return True

    if re.search(r"\breschedule\b.*\bgoal(?:s)?\b", normalized):
        return True
    return bool(
        re.search(r"\b(?:change|move|push)\b", normalized)
        and re.search(r"\b(?:deadline|target date)\b", normalized)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to allowlisted, non-command text messages."""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    if str(chat_id) != str(MY_CHAT_ID):
        logger.warning("Blocked message from unauthorized chat ID: %s", chat_id)
        return

    user_text = update.message.text
    logger.info("Incoming message from %s: %r", chat_id, user_text)

    # Build context BEFORE logging user message to avoid duplicate current turn in transcript
    system_prompt = get_formatted_system_prompt(
        include_goals=_needs_active_goal_context(user_text)
    )

    try:
        reply_result = await asyncio.to_thread(get_reply, system_prompt, user_text)
        reply_text = _plain_text_for_telegram(reply_result["text"])
        state_change_attempted = reply_result["state_change_attempted"]
    except Exception:
        logger.exception("LLM generation or tool loop failed")
        await update.message.reply_text(
            "Sorry, I couldn't reach my AI service right now. Please try again shortly."
        )
        return

    # Persist both sides of the successful turn only after context assembly
    # and LLM processing are complete. This keeps the current user message
    # out of the historical context used for this request.
    log_message("user", user_text)
    logger.info("Luna reply: %r", reply_text)
    log_message("luna", reply_text)
    await update.message.reply_text(reply_text)

    # Memory formation is secondary to the conversation.  Send Luna's reply
    # first, then run the synchronous memory extractor off the event loop.
    if user_text.strip() and not state_change_attempted:
        try:
            saved_count = await asyncio.to_thread(
                process_turn_memory,
                user_text,
                groq_client,
            )
            logger.info("Memory formation completed: %d fact(s) saved.", saved_count)
        except Exception:
            logger.exception("Memory formation failed after successful response")


def validate_configuration() -> None:
    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": TOKEN,
            "MY_CHAT_ID": MY_CHAT_ID,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )


_REGISTERED_SCHEDULER_JOBS: list[tuple[object, set[str]]] = []


def _get_registered_scheduler_jobs(app) -> set[str]:
    for registered_app, jobs in _REGISTERED_SCHEDULER_JOBS:
        if registered_app is app:
            return jobs

    jobs = set()
    _REGISTERED_SCHEDULER_JOBS.append((app, jobs))
    return jobs


def register_job_queue_jobs(app) -> None:
    """Register Moon's scheduler jobs once for this application instance."""
    if app.job_queue is None:
        logger.error("JobQueue is not available. Scheduled jobs will not run.")
        return

    registered_jobs = _get_registered_scheduler_jobs(app)
    jobs = (
        ("reminders", check_due_reminders, 60, 10),
        ("proactive_check_ins", check_proactive_triggers, 900, 60),
    )

    for job_name, callback, interval, first in jobs:
        if job_name in registered_jobs:
            continue

        try:
            app.job_queue.run_repeating(
                callback,
                interval=interval,
                first=first,
            )
        except Exception:
            logger.exception("Failed to register %s scheduler job", job_name)
            continue

        registered_jobs.add(job_name)


def main() -> None:
    validate_configuration()
    init_db()  # Runs safely on application startup only

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    register_job_queue_jobs(app)

    logger.info("Luna (Tool Loop Enabled) is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
