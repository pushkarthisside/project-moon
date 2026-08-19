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
from scheduler import check_due_reminders

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _plain_text_for_telegram(text: str) -> str:
    """Remove common Markdown delimiters because replies use plain Telegram text."""
    text = re.sub(r"```(?:[^\n]*)\n?", "", text)
    text = text.replace("```", "")
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"\1", text)
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
    return any(word in normalized for word in completion_words + removal_words)


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


def main() -> None:
    validate_configuration()
    init_db()  # Runs safely on application startup only

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize the scheduler loop
    # Runs the check every 60 seconds, starting 10 seconds after bot boot
    if app.job_queue is None:
        logger.error("JobQueue is not available. Reminders will not be dispatched.")
    else:
        try:
            app.job_queue.run_repeating(
                check_due_reminders,
                interval=60,
                first=10,
            )
            logger.info("Reminder scheduler initialized.")
        except Exception:
            logger.exception(
                "Failed to register reminder scheduler. "
                "Reminders will not be dispatched."
            )

    logger.info("Luna (Tool Loop Enabled) is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
