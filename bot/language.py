DEFAULT_LANG = "en"

MESSAGES = {
    "it": {
        "welcome": (
            "Ciao {name}! 👋\n\n"
            "Monitoro i prezzi dei prodotti e ti avviso quando scendono.\n"
            "⚠️ Per ora funziono solo con link Amazon.\n\n"
            "📄 Comandi disponibili:\n"
            "/track <url> [prezzo] — aggiunge un prodotto (soglia opzionale)\n"
            "/list — mostra i prodotti che segui\n"
            "/untrack <id> — smette di seguire un prodotto\n"
            "/show_history <id> — mostra lo storico prezzi di un prodotto"
        ),
        "track_usage": "Uso: /track <link Amazon> [prezzo]",
        "track_unsupported": "Per ora seguo solo link Amazon. 🙈",
        "track_ok": "✅ Ora seguo «{name}» a {price}{currency}. Ti avviso quando scende!",
        "track_ok_target": "✅ Ora seguo «{name}» a {price}{currency}. Ti avviso quando scende sotto {target}{currency}!",
        "track_error": "😕 Non riesco a leggere il prezzo da questo link",
        "track_bad_target": "La soglia dev'essere un numero positivo. Esempio: /track <link> 130",
        "track_limit": "⚠️ Hai raggiunto il limite di {max} prodotti seguiti: rimuovine qualcuno con /untrack.",
        "display_tracked": "Ecco la lista dei prodotti seguiti:\n{items}",
        "last_price": "ultimo prezzo",
        "target": "soglia",
        "empty_list": "Non sono presenti prodotti seguiti!",
        "missing_id": "Inserire l'id del prodotto!",
        "missing_product_untrack": "Il prodotto {id} non è seguito!",
        "id_error": "Errore! L'id non è valido!",
        "untrack_ok": "✅ Il prodotto {id} è stato rimosso dalla watch list!",
        "price_drop": "📉 Il prezzo di «{name}» è sceso da {old}{currency} a {new}{currency}!",
        "check_broken": "⚠️ Non riesco più a leggere il prezzo di «{name}». Continuerò a riprovare!",
        "missing_values": "Non sono presenti valori per il prodotto {id}",
        "display_history": (
            "Prezzi registrati per «{name}»: \n{items}\n"
            "Media: {mean} €"
        ),
        "cmd_track": "Aggiungi un prodotto da monitorare",
        "cmd_list": "Mostra i prodotti che segui",
        "cmd_untrack": "Smetti di seguire un prodotto",
        "cmd_history": "Ottieni lo storico di un prodotto",
    },
    "en": {
        "welcome": (
            "Hi {name}! 👋\n\n"
            "I track product prices and alert you when they drop.\n"
            "⚠️ For now I only work with Amazon links.\n\n"
            "📄 Available commands:\n"
            "/track <url> [price] — add a product (optional price threshold)\n"
            "/list — show the products you follow\n"
            "/untrack <id> — stop following a product\n"
            "/show_history <id> — show a product's price history"
        ),
        "track_usage": "Usage: /track <Amazon link> [price]",
        "track_unsupported": "For now I only track Amazon links. 🙈",
        "track_ok": "✅ Now tracking «{name}» at {price}{currency}. I'll let you know when it drops!",
        "track_ok_target": "✅ Now tracking «{name}» at {price}{currency}. I'll alert you when it drops below {target}{currency}!",
        "track_error": "😕 I couldn't read the price from this link",
        "track_bad_target": "The threshold must be a positive number. Example: /track <link> 130",
        "track_limit": "⚠️ You've reached the limit of {max} tracked products: remove some with /untrack.",
        "display_tracked": "Here are the products you follow:\n{items}",
        "last_price": "last price",
        "target": "target",
        "empty_list": "You are not following any product yet!",
        "missing_id": "Insert the id of the product!",
        "missing_product_untrack": "The product {id} is not tracked!",
        "id_error": "Error! The id is not valid!",
        "untrack_ok": "✅ The product {id} has been removed from the watch list!",
        "price_drop": "📉 The price of «{name}» dropped from {old}{currency} to {new}{currency}!",
        "check_broken": "⚠️ I can no longer read the price of «{name}». I'll keep trying!",
        "missing_values": "No records are available for product {id}",
        "display_history": (
            "Recorded prices for «{name}»: \n{items}\n"
            "Mean: {mean} €"
        ),
        "cmd_track": "Add a product to monitor",
        "cmd_list": "Show the products you follow",
        "cmd_untrack": "Stop following a product",
        "cmd_history": "Get a product's price history",
    },
}


def translate(key: str, lang: str | None, **kwargs) -> str:
    lang = (lang or DEFAULT_LANG).split("-")[0]
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return text.format(**kwargs)
