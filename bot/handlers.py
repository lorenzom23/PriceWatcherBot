import asyncio
from datetime import datetime
from urllib.parse import urlparse

from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import MessageHandler, CommandHandler, ConversationHandler, filters

import config
from bot.language import translate
from core.checker import check_all
from core.models import House
from scrapers.registry import get_scraper
from storage.repository import (
    add_product, add_price, add_subscription, get_subscriptions,
    remove_subscription, remove_chat_subscriptions, save_user,
    get_user_language, get_history, get_last_price,
    change_target, remove_target, get_product_url, get_houses, add_houses,
    get_house_searches_for_chat, remove_house_search
)

SELECT_ID = 1
WAITING_URL = 2
WAITING_TARGET = 3
SELECT_UNTRACK_ID = 4
WAITING_TARGET_ID = 5
WAITING_TARGET_PRICE = 6
SELECT_RESET_TARGET_ID = 7

authorized_users = (
    filters.ALL
    if not config.AUTH_USER_IDS
    else filters.User(config.AUTH_USER_IDS)
)


def _parse_target(text: str) -> float:
    """Raises ValueError if text isn't a valid positive target price."""
    value = float(text)
    if not 0 < value < 1e9:  # esclude anche nan/inf, che float() accetta
        raise ValueError
    return value


def _format_tracked_list(res) -> str:
    """id + nome per ogni prodotto seguito, per aiutare a scegliere quale id inserire."""
    return "\n".join(f"[{seq}] {name[:40]}" for seq, _, name, _ in res)


def _format_tracked_build_list(tracked_list) -> str:
    return "\n".join(
        f"[{item['sequence']}] {item['description']}"
        for item in tracked_list
    )


def _build_tracked_list(res, house_searches) -> list[dict]:
    tracked_list = [
        {
            "sequence": sequence,
            "description": name,
            "id": prod_id,
        }
        for sequence, prod_id, name, _ in res
    ]
    first_house_id = max((item["sequence"] for item in tracked_list), default=0) + 1
    tracked_list.extend(
        {
            "sequence": sequence,
            "description": house_link[0],
            'id': None
        }
        for sequence, house_link in enumerate(house_searches, start=first_house_id)
    )
    return tracked_list


def _is_list_of_houses(result) -> bool:
    return isinstance(result, list) and all(isinstance(house, House) for house in result)


async def cancel(update, context):
    lang = update.effective_user.language_code
    context.user_data.clear()
    await update.message.reply_text(translate("cancelled", lang))
    return ConversationHandler.END


async def start(update, context):
    lang = update.effective_user.language_code
    name = update.effective_user.first_name
    save_user(update.effective_chat.id, lang)
    await update.message.reply_text(translate("welcome", lang, name=name))


async def show_history(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang, items=_format_tracked_list(res)))
        return SELECT_ID

    try:
        history_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return ConversationHandler.END

    await update.message.reply_text(_do_show_history(chat_id, lang, history_id))
    return ConversationHandler.END


async def show_history_receive_id(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    try:
        history_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return SELECT_ID  # ridomanda

    await update.message.reply_text(_do_show_history(chat_id, lang, history_id))
    return ConversationHandler.END


async def _fetch_product(url):
    """Valida e scarica un prodotto."""
    try:
        scraper = get_scraper(url)
    except ValueError:
        err = "track_unsupported"
        return None, err
    try:
        return await asyncio.to_thread(scraper.fetch, url), None
    except Exception as e:
        print(f"Error during scrape of {url}: {e}")
        err = "track_error"
        return None, err


async def _save_tracking(update, chat_id, url, result, target_price, lang):
    """Ultimo passo comune: salva prodotto/prezzo/sottoscrizione e conferma all'utente."""
    if _is_list_of_houses(result):
        existing = get_houses(chat_id, url)
        if not existing:
            add_houses(chat_id, url, result)
            await update.message.reply_text(translate("track_houses_ok", lang, count=len(result)))
        else:
            await update.message.reply_text(translate("track_houses_existing", lang, count=len(existing)))
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


async def track(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    save_user(chat_id, lang)

    # prima dello scrape: a limite raggiunto non si spende neanche la richiesta HTTP
    if len(get_subscriptions(chat_id)) >= config.MAX_TRACKED_PER_CHAT:
        await update.message.reply_text(translate("track_limit", lang, max=config.MAX_TRACKED_PER_CHAT))
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text(translate("track_ask_url", lang))
        return WAITING_URL

    url = context.args[0]

    target_price = None
    if len(context.args) > 1:
        try:
            target_price = _parse_target(context.args[1])
        except ValueError:
            await update.message.reply_text(translate("track_bad_target", lang))
            return ConversationHandler.END

    result, err = await _fetch_product(url)
    if result is None:
        await update.message.reply_text(translate(err, lang))
        return WAITING_URL if err == "track_error" else ConversationHandler.END

    await _save_tracking(update, chat_id, url, result, target_price, lang)
    return ConversationHandler.END


async def track_receive_url(update, context):
    lang = update.effective_user.language_code
    url = update.message.text.strip()

    result, err = await _fetch_product(url)
    if result is None:
        await update.message.reply_text(translate(err, lang))
        return WAITING_URL if err == "track_error" else ConversationHandler.END

    if _is_list_of_houses(result):
        await _save_tracking(update, update.effective_chat.id, url, result, None, lang)
        return ConversationHandler.END

    context.user_data["track_url"] = url
    context.user_data["track_result"] = result
    await update.message.reply_text(
        translate("track_found", lang, name=result.name, price=result.price, currency=result.currency)
    )
    return WAITING_TARGET


async def track_skip_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    url = context.user_data.pop("track_url", None)
    result = context.user_data.pop("track_result", None)
    if url is None or result is None:
        return ConversationHandler.END  # stato incoerente: niente da salvare

    await _save_tracking(update, chat_id, url, result, None, lang)
    return ConversationHandler.END


async def track_receive_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    try:
        target_price = _parse_target(update.message.text)
    except ValueError:
        await update.message.reply_text(translate("track_bad_target", lang))
        return WAITING_TARGET  # ridomanda la soglia

    url = context.user_data.pop("track_url", None)
    result = context.user_data.pop("track_result", None)
    if url is None or result is None:
        return ConversationHandler.END

    await _save_tracking(update, chat_id, url, result, target_price, lang)
    return ConversationHandler.END


async def list_tracked(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)
    house_searches = get_house_searches_for_chat(chat_id)

    if not res and not house_searches:
        await update.message.reply_text(translate("empty_list", lang))
        return
    text = ''
    if res:
        # nome accorciato + ultimo prezzo (+ soglia se impostata); col cap di prodotti sta nei 4096 char
        last_label = translate("last_price", lang)
        target_label = translate("target", lang)
        text = "\n".join(
            f"[{seq}] {p_name[:40]} — {last_label}: {get_last_price(pid)}€"
            + (f" ({target_label}: {target}€)" if target is not None else "")
            for seq, pid, p_name, target in res
        )
    if house_searches:
        sequence = max((item[0] for item in res), default=0) + 1
        house_text = "\n".join(
            f"[{count}] {house_link[0]}"
            for count, house_link in enumerate(house_searches, start=sequence)
        )
        text += f"\n{house_text}"
    await update.message.reply_text(translate("display_tracked", lang, items=text))


def _do_untrack(chat_id, untrack_id, tracked_list) -> str:
    item_to_untrack = next((item for item in tracked_list if item["sequence"] == untrack_id), None)
    if item_to_untrack is None:
        return "id_error"

    if item_to_untrack["id"] is None:
        remove_house_search(chat_id, untrack_id)
    else:
        remove_subscription(chat_id, item_to_untrack["id"])
    return None


async def untrack(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)
    house_searches = get_house_searches_for_chat(chat_id)

    if not res and not house_searches:
        await update.message.reply_text(translate("empty_list", lang))
        return ConversationHandler.END

    tracked_list = _build_tracked_list(res, house_searches)
    if not context.args:
        context.user_data["tracked_list"] = tracked_list
        await update.message.reply_text(translate("missing_id", lang, items=_format_tracked_build_list(tracked_list)))
        return SELECT_UNTRACK_ID

    try:
        untrack_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return ConversationHandler.END
    err = _do_untrack(chat_id, untrack_id, tracked_list)
    if err:
        await update.message.reply_text(translate(err, lang))
        return ConversationHandler.END
    await update.message.reply_text(translate("untrack_ok", lang, id=untrack_id))
    return ConversationHandler.END


async def untrack_receive_id(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    try:
        untrack_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return SELECT_UNTRACK_ID  # ridomanda

    tracked_list = context.user_data.pop("tracked_list", None)
    err = _do_untrack(chat_id, untrack_id, tracked_list)
    if err:
        await update.message.reply_text(translate(err, lang))
    else:
        await update.message.reply_text(translate("untrack_ok", lang, id=untrack_id))
    return ConversationHandler.END


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


def _do_show_history(chat_id, lang, history_id) -> str:
    # il numero è per-utente: si risolve solo dentro le sottoscrizioni della chat, niente storico altrui
    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == history_id), None)
    if match is None:
        return translate("product_not_tracked", lang, id=history_id)
    product_id, product_name = match

    res = get_history(product_id)
    if not res:
        return translate("missing_values", lang, id=history_id)

    prices = [p_price for p_price, _ in res]
    mean = round(sum(prices) / len(prices), 2)
    # Telegram tronca a 4096 char: mostra solo gli ultimi punti, la media resta su tutto

    last_price = None
    res_to_print = []
    for price, ts in res:
        if last_price != price:
            res_to_print.append((price, ts))
            last_price = price

    text = "\n".join(f"{timestamp[:16].replace('T', ' ')}: {p_price} €" for p_price, timestamp in res_to_print[-10:])
    url = get_product_url(product_id)
    return translate("display_history", lang, name=product_name[:60], items=text, mean=mean, url=url)


def _do_reset_target(chat_id, lang, target_id) -> str:
    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == target_id), None)
    if match is None:
        return translate("product_not_tracked", lang, id=target_id)
    product_id, name = match

    remove_target(chat_id, product_id)
    return translate("target_removed", lang, name=name[:60])


async def reset_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang, items=_format_tracked_list(res)))
        return SELECT_RESET_TARGET_ID

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return ConversationHandler.END

    await update.message.reply_text(_do_reset_target(chat_id, lang, target_id))
    return ConversationHandler.END


async def reset_target_receive_id(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    try:
        target_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return SELECT_RESET_TARGET_ID  # ridomanda

    await update.message.reply_text(_do_reset_target(chat_id, lang, target_id))
    return ConversationHandler.END


async def set_target(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id
    res = get_subscriptions(chat_id)

    if not res:
        await update.message.reply_text(translate("empty_list", lang))
        return ConversationHandler.END

    if not context.args:
        await update.message.reply_text(translate("missing_id", lang, items=_format_tracked_list(res)))
        return WAITING_TARGET_ID

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return ConversationHandler.END

    match = next(((pid, name) for seq, pid, name, _ in res if seq == target_id), None)
    if match is None:
        await update.message.reply_text(translate("product_not_tracked", lang, id=target_id))
        return ConversationHandler.END
    product_id, name = match

    if len(context.args) < 2:
        # id valido ma manca il prezzo: lo chiediamo, ricordandoci il prodotto
        context.user_data["target_product_id"] = product_id
        context.user_data["target_product_name"] = name
        await update.message.reply_text(translate("ask_target_price", lang))
        return WAITING_TARGET_PRICE

    try:
        new_target = _parse_target(context.args[1])
    except ValueError:
        await update.message.reply_text(translate("track_bad_target", lang))
        return ConversationHandler.END

    change_target(chat_id, product_id, new_target)
    await update.message.reply_text(translate("target_updated", lang, name=name[:60], target=new_target))
    return ConversationHandler.END


async def set_target_receive_id(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    try:
        target_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text(translate("id_error", lang))
        return WAITING_TARGET_ID  # ridomanda

    match = next(((pid, name) for seq, pid, name, _ in get_subscriptions(chat_id) if seq == target_id), None)
    if match is None:
        await update.message.reply_text(translate("product_not_tracked", lang, id=target_id))
        return ConversationHandler.END
    product_id, name = match

    context.user_data["target_product_id"] = product_id
    context.user_data["target_product_name"] = name
    await update.message.reply_text(translate("ask_target_price", lang))
    return WAITING_TARGET_PRICE


async def set_target_receive_price(update, context):
    lang = update.effective_user.language_code
    chat_id = update.effective_chat.id

    try:
        new_target = _parse_target(update.message.text)
    except ValueError:
        await update.message.reply_text(translate("track_bad_target", lang))
        return WAITING_TARGET_PRICE  # ridomanda

    product_id = context.user_data.pop("target_product_id", None)
    name = context.user_data.pop("target_product_name", None)
    if product_id is None:
        return ConversationHandler.END  # stato incoerente: niente da salvare

    change_target(chat_id, product_id, new_target)
    await update.message.reply_text(translate("target_updated", lang, name=name[:60], target=new_target))
    return ConversationHandler.END


conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler("track", track, filters=authorized_users),
        CommandHandler("untrack", untrack, filters=authorized_users),
        CommandHandler("show_history", show_history, filters=authorized_users),
        CommandHandler("set_target", set_target, filters=authorized_users),
        CommandHandler("reset_target", reset_target, filters=authorized_users),
    ],
    states={
        SELECT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, show_history_receive_id)],
        WAITING_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, track_receive_url)],
        WAITING_TARGET: [
            CommandHandler("skip", track_skip_target),
            MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, track_receive_target),
        ],
        SELECT_UNTRACK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, untrack_receive_id)],
        WAITING_TARGET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, set_target_receive_id)],
        WAITING_TARGET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, set_target_receive_price)],
        SELECT_RESET_TARGET_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & authorized_users, reset_target_receive_id)],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, cancel)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel, filters=authorized_users),
        CommandHandler("track", track, filters=authorized_users),
        CommandHandler("untrack", untrack, filters=authorized_users),
        CommandHandler("show_history", show_history, filters=authorized_users),
        CommandHandler("set_target", set_target, filters=authorized_users),
        CommandHandler("reset_target", reset_target, filters=authorized_users),
    ],
    conversation_timeout=180,
)
