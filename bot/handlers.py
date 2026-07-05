from datetime import datetime
from urllib.parse import urlparse

from bot.language import translate
from scrapers.registry import get_scraper
from storage.repository import add_product, add_price, add_subscription, get_subscriptions


async def start(update, context):
    lang = update.effective_user.language_code
    name = update.effective_user.first_name
    await update.message.reply_text(translate("welcome", lang, name=name))


async def track(update, context):
    lang = update.effective_user.language_code

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
