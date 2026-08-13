import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from context import get_formatted_system_prompt
from db import init_db, log_message
from llm import get_reply, groq_client
from memory import process_turn_memory

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


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
    system_prompt = get_formatted_system_prompt()

    # Log incoming user message
    log_message("user", user_text)

    try:
        reply_text = await asyncio.to_thread(get_reply, system_prompt, user_text)
    except Exception:
        logger.exception("LLM generation or tool loop failed")
        await update.message.reply_text(
            "Sorry, I couldn't reach my AI service right now. Please try again shortly."
        )
        return

    logger.info("Luna reply: %r", reply_text)
    log_message("luna", reply_text)
    await update.message.reply_text(reply_text)

    # Memory formation is secondary to the conversation.  Send Luna's reply
    # first, then run the synchronous memory extractor off the event loop.
    if user_text.strip():
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

    logger.info("Luna (Tool Loop Enabled) is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
