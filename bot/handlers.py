from datetime import datetime
from urllib.parse import urlparse

from bot.language import translate
from scrapers.registry import get_scraper
from storage.repository import (
    add_product, add_price, add_subscription, get_subscriptions,
    remove_subscription, save_user,
)


async def start(update, context):
    lang = update.effective_user.language_code
    name = update.effective_user.first_name
    save_user(update.effective_chat.id, lang)
    await update.message.reply_text(translate("welcome", lang, name=name))


async def track(update, context):
    lang = update.effective_user.language_code
    save_user(update.effective_chat.id, lang)

    if not context.args:
        await update.message.reply_text(translate("track_usage", lang))
        return

    url = context.args[0]
    chat_id = update.effective_chat.id
    try:
        scraper = get_scraper(url)
    except ValueError:
        await update.message.reply_text(translate("track_unsupported", lang))
        return

    result = scraper.fetch(url)
    website = urlparse(url).netloc

    product_id = add_product(url, result.name, website)
    add_price(product_id, result.price, datetime.now().isoformat())
    add_subscription(chat_id, product_id)

    await update.message.reply_text(
        translate("track_ok", lang, name=result.name, price=result.price)
    )


async def list_tracked(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return

    text = "\n".join(f"[{p_id}] {p_name}" for p_id, p_name in res)

    await update.message.reply_text(translate("display_tracked", lang, products=text))


async def untrack_product(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return

    if not context.args:
        await update.message.reply_text(translate("missing_id_untrack", lang))
        return
    try:
        untrack_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_untrack_error", lang))
        return

    is_tracked = any((p_id, p_name) for p_id, p_name in res if p_id == untrack_id)
    if not is_tracked:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=untrack_id))
        return

    remove_subscription(chat_id, untrack_id)
    await update.message.reply_text(translate("untrack_ok", lang, id=untrack_id))
