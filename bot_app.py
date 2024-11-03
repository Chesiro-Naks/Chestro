import os
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import traceback

# Initialize Flask app, to keep the flow,
app = Flask(__name__)

# A health check endpoint, it runs on the low,
@app.route('/')
def home():
    return "Bot is running! It's all in the show!"

# Your bot setup and handlers come next, 
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome! Send me a URL to scrape live match details and get all links.")

async def handle_message(update: Update, context: CallbackContext):
    # Your bot handling code here
    pass

def run_bot():
    bot_app = Application.builder().token("7697105114:AAFkQ-uVxKaZRG97fzxIqRQtSiM-vaIMUjk").build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    bot_app.run_polling()

def main():
    # Start Flask server in a thread, to keep the web alive,
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))).start()
    # Start the bot, let it thrive,
    run_bot()

if __name__ == "__main__":
    main()
