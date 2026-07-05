from bot.language import translate

async def start(update, context):
    lang = update.effective_user.language_code
    name = update.effective_user.first_name
    await update.message.reply_text(translate("welcome", lang, name=name))
