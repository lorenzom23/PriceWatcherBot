import asyncio
from datetime import datetime
from urllib.parse import urlparse

from telegram.error import Forbidden

from bot.language import translate
from core.checker import check_all
from scrapers.registry import get_scraper
from storage.repository import (
    add_product, add_price, add_subscription, get_subscriptions,
    remove_subscription, remove_chat_subscriptions, save_user,
    get_user_language, get_history
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

    target_price = None
    if len(context.args) > 1:
        try:
            target_price = float(context.args[1])
        except ValueError:
            await update.message.reply_text(translate("track_bad_target", lang))
            return

    try:
        scraper = get_scraper(url)
    except ValueError:
        await update.message.reply_text(translate("track_unsupported", lang))
        return

    try:
        result = await asyncio.to_thread(scraper.fetch, url)
    except Exception:
        await update.message.reply_text(translate("track_error", lang))
        return

    website = urlparse(url).netloc
    product_id, created = add_product(url, result.name, website)
    if created:
        # se il prodotto esiste già lo storico è alimentato dal job: niente punti doppi
        add_price(product_id, result.price, datetime.now().isoformat())
    add_subscription(chat_id, product_id, target_price)

    if target_price is None:
        await update.message.reply_text(
            translate("track_ok", lang, name=result.name, price=result.price)
        )
    else:
        await update.message.reply_text(
            translate("track_ok_target", lang, name=result.name, price=result.price, target=target_price)
        )


async def list_tracked(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return

    text = "\n".join(f"[{p_id}] {p_name}" for p_id, p_name in res)

    await update.message.reply_text(translate("display_tracked", lang, items=text))


async def untrack_product(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang))
        return
    try:
        untrack_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return

    is_tracked = any((p_id, p_name) for p_id, p_name in res if p_id == untrack_id)
    if not is_tracked:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=untrack_id))
        return

    remove_subscription(chat_id, untrack_id)
    await update.message.reply_text(translate("untrack_ok", lang, id=untrack_id))


async def check_prices_job(context):
    # check_all() does blocking network + DB I/O; run the whole batch off the event loop.
    # It runs in a single worker thread, so every SQLite connection stays thread-local.
    for chat_id, name, old, new in await asyncio.to_thread(check_all):
        lang = get_user_language(chat_id)
        text = translate("price_drop", lang, name=name, old=old, new=new)
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Forbidden:
            remove_chat_subscriptions(chat_id)


async def get_product_history(update, context):
    lang = update.effective_user.language_code

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang))
        return
    try:
        history_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return

    res = get_history(history_id)
    if not res:
        await update.message.reply_text(translate("missing_values", lang, id=history_id))
        return

    text = "\n".join(f"{timestamp[:16].replace('T', ' ')}: {p_price} €" for p_price, timestamp in res)
    prices = [p_price for p_price, _ in res]
    mean = round(sum(prices) / len(prices), 2)
    await update.message.reply_text(translate("display_history", lang, id=history_id, items=text, mean=mean))
