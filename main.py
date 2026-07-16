from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler
import config
from storage.database import init_db
from bot.handlers import (
    start, list_tracked, check_prices_job, reset_target,
    conv_handler, track_conv_handler, untrack_conv_handler, set_target_conv_handler
)
from bot.language import translate
from telegram import BotCommand

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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(track_conv_handler)
    app.add_handler(CommandHandler("list", list_tracked))
    app.add_handler(untrack_conv_handler)
    app.add_handler(conv_handler)

    app.add_handler(set_target_conv_handler)
    app.add_handler(CommandHandler("reset_target", reset_target))

    app.job_queue.run_repeating(
        check_prices_job,
        interval=config.CHECK_INTERVAL_HOURS * 3600,
        first=300,  # un crash-loop del container non deve martellare i siti ad ogni riavvio
    )

    app.run_polling()

if __name__ == "__main__":
    main()
