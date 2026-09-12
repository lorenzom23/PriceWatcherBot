import config
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from storage.database import init_db
from bot.handlers import (
    start, list_tracked, check_prices_job, conversation_handler, authorized_users
)
from bot.language import translate


def build_commands(lang):
    return [
        BotCommand("track", translate("cmd_track", lang)),
        BotCommand("list", translate("cmd_list", lang)),
        BotCommand("untrack", translate("cmd_untrack", lang)),
        BotCommand("show_history", translate("cmd_history", lang)),
        BotCommand("set_target", translate("cmd_set_target", lang)),
        BotCommand("reset_target", translate("cmd_reset_target", lang)),
    ]


async def post_init(app):
    await app.bot.set_my_commands(build_commands("en"))                     # default per tutti
    await app.bot.set_my_commands(build_commands("it"), language_code="it")


def main():
    init_db()
    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start, filters=authorized_users))
    app.add_handler(CommandHandler("list", list_tracked, filters=authorized_users))
    app.add_handler(conversation_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, start))

    app.job_queue.run_repeating(
        check_prices_job,
        interval=config.CHECK_INTERVAL_HOURS * 3600,
        first=300,  # un crash-loop del container non deve martellare i siti ad ogni riavvio
    )

    app.run_polling()


if __name__ == "__main__":
    main()
