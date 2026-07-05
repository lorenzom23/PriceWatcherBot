from telegram.ext import ApplicationBuilder, CommandHandler
import config
from storage.database import init_db
from bot.handlers import start

def main():
    init_db()
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
