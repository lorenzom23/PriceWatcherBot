import asyncio
from datetime import datetime
from urllib.parse import urlparse

from telegram.error import Forbidden, RetryAfter, TelegramError

import config
from bot.language import translate
from core.checker import check_all
from scrapers.registry import get_scraper
from storage.repository import (
    add_product, add_price, add_subscription, get_subscriptions,
    remove_subscription, remove_chat_subscriptions, save_user,
    get_user_language, get_history, get_last_price,
    change_target, remove_target
)


def _parse_target(text: str) -> float:
    """Raises ValueError if text isn't a valid positive target price."""
    value = float(text)
    if not 0 < value < 1e9:  # esclude anche nan/inf, che float() accetta
        raise ValueError
    return value


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

    # prima dello scrape: a limite raggiunto non si spende neanche la richiesta HTTP
    if len(get_subscriptions(chat_id)) >= config.MAX_TRACKED_PER_CHAT:
        await update.message.reply_text(translate("track_limit", lang, max=config.MAX_TRACKED_PER_CHAT))
        return

    target_price = None
    if len(context.args) > 1:
        try:
            target_price = _parse_target(context.args[1])
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
            translate("track_ok", lang, name=result.name, price=result.price, currency=result.currency)
        )
    else:
        await update.message.reply_text(
            translate("track_ok_target", lang, name=result.name, price=result.price,
                      target=target_price, currency=result.currency)
        )


async def list_tracked(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return

    # nome accorciato + ultimo prezzo (+ soglia se impostata); col cap di prodotti sta nei 4096 char
    last_label = translate("last_price", lang)
    target_label = translate("target", lang)
    text = "\n".join(
        f"[{seq}] {p_name[:40]} — {last_label}: {get_last_price(pid)}€"
        + (f" ({target_label}: {target}€)" if target is not None else "")
        for seq, pid, p_name, target in res
    )

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

    product_id = next((pid for seq, pid, _, _ in res if seq == untrack_id), None)
    if product_id is None:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=untrack_id))
        return

    remove_subscription(chat_id, product_id)
    await update.message.reply_text(translate("untrack_ok", lang, id=untrack_id))


async def check_prices_job(context):
    # check_all() does blocking network + DB I/O; run the whole batch off the event loop.
    # It runs in a single worker thread, so every SQLite connection stays thread-local.
    for message_key, chat_id, params in await asyncio.to_thread(check_all):
        lang = get_user_language(chat_id)
        text = translate(message_key, lang, **params)
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Forbidden:
            remove_chat_subscriptions(chat_id)
        except RetryAfter as e:
            # flood control: rispetta l'attesa richiesta da Telegram e ritenta una volta
            await asyncio.sleep(e.retry_after + 1)
            try:
                await context.bot.send_message(chat_id=chat_id, text=text)
            except TelegramError as retry_err:
                print(f"Alert perso per chat {chat_id}: {retry_err}")
        except TelegramError as e:
            # il prezzo nuovo è già in history, questo alert non verrà rigenerato:
            # perderne uno è inevitabile, perdere anche i successivi del giro no
            print(f"Alert perso per chat {chat_id}: {e}")


async def get_product_history(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang))
        return
    try:
        history_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return

    # il numero è per-utente: si risolve solo dentro le sottoscrizioni della chat, niente storico altrui
    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == history_id), None)
    if match is None:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=history_id))
        return
    product_id, product_name = match

    res = get_history(product_id)
    if not res:
        await update.message.reply_text(translate("missing_values", lang, id=history_id))
        return

    prices = [p_price for p_price, _ in res]
    mean = round(sum(prices) / len(prices), 2)
    # Telegram tronca a 4096 char: mostra solo gli ultimi punti, la media resta su tutto
    text = "\n".join(f"{timestamp[:16].replace('T', ' ')}: {p_price} €" for p_price, timestamp in res[-30:])
    await update.message.reply_text(translate("display_history", lang, name=product_name[:60], items=text, mean=mean))


async def reset_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang))
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return
    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == target_id), None)
    if match is None:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=target_id))
        return
    product_id, name = match

    remove_target(chat_id, product_id)
    await update.message.reply_text(translate("target_removed", lang, name=name[:60]))


async def set_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    if len(context.args) < 2:
        await update.message.reply_text(translate("set_target_usage", lang))
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return
    try:
        new_target = _parse_target(context.args[1])
    except ValueError:
        await update.message.reply_text(translate("track_bad_target", lang))
        return

    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == target_id), None)
    if match is None:
        await update.message.reply_text(translate("missing_product_untrack", lang, id=target_id))
        return
    product_id, name = match

    change_target(chat_id, product_id, new_target)
    await update.message.reply_text(translate("target_updated", lang, name=name[:60], target=new_target))

