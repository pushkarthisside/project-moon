import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# 1. Load environment variables from the .env file
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# 2. Configure basic console logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 3. Define the handler function for incoming text messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Retrieve the chat_id and message text from the update object
    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Print the sender's chat_id to the console
    print(f"\n[INCOMING MESSAGE] Chat ID: {chat_id} | Message: '{user_text}'\n")

    # Echo the text back to the Telegram chat
    await update.message.reply_text(user_text)

if __name__ == '__main__':
    # Guard clause to ensure the token exists before running
    if not TOKEN:
        raise ValueError("Error: TELEGRAM_BOT_TOKEN is missing from your .env file!")

    # Build the Telegram Bot application instance
    app = ApplicationBuilder().token(TOKEN).build()

    # Register the echo handler to listen for non-command text messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

    print("Luna Echo Bot is running... Press Ctrl+C to stop.")
    app.run_polling()