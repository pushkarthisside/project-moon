import asyncio
import logging
import os

from dotenv import load_dotenv
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from db import init_db, log_message


load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = "You are Luna, a warm, helpful companion."

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Single client instance initialized once at module load
groq_client = Groq(api_key=GROQ_API_KEY)


def get_reply(user_text: str) -> str:
    """Get a completion from Groq using the persistent client instance."""
    completion = groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    return completion.choices[0].message.content or "I couldn't generate a response."


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to allowlisted, non-command text messages."""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    if str(chat_id) != str(MY_CHAT_ID):
        logger.warning("Blocked message from unauthorized chat ID: %s", chat_id)
        return

    user_text = update.message.text
    log_message("user", user_text)
    logger.info("Incoming message from %s: %r", chat_id, user_text)

    try:
        reply_text = await asyncio.to_thread(get_reply, user_text)
    except Exception:
        logger.exception("Groq request failed")
        await update.message.reply_text(
            "Sorry, I couldn't reach my AI service right now. Please try again shortly."
        )
        return

    logger.info("Luna reply: %r", reply_text)
    log_message("luna", reply_text)
    await update.message.reply_text(reply_text)


def validate_configuration() -> None:
    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": TOKEN,
            "GROQ_API_KEY": GROQ_API_KEY,
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

    logger.info("Luna (powered by Groq) is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()