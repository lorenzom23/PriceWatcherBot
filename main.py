from telegram.ext import ApplicationBuilder, CommandHandler
import config
from storage.database import init_db
from bot.handlers import start, track, list_tracked, untrack_product, check_prices_job

def main():
    init_db()
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("list", list_tracked))
    app.add_handler(CommandHandler("untrack", untrack_product))

    app.job_queue.run_repeating(
        check_prices_job,
        interval=config.CHECK_INTERVAL_HOURS * 3600,
        first=10,
    )

    app.run_polling()

if __name__ == "__main__":
    main()
