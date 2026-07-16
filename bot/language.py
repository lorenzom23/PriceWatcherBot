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
            "/show_history <id> — mostra lo storico prezzi di un prodotto\n"
            "/set_target <id> <prezzo> — imposta/aggiorna la soglia di un prodotto\n"
            "/reset_target <id> — rimuove la soglia di un prodotto"
        ),
        "track_usage": "Uso: /track <link Amazon> [prezzo]",
        "track_unsupported": "Per ora seguo solo link Amazon. 🙈",
        "track_ok": "✅ Ora seguo «{name}» a {price}{currency}. Ti avviso quando scende!",
        "track_ok_target": "✅ Ora seguo «{name}» a {price}{currency}. Ti avviso quando scende sotto {target}{currency}!",
        "track_error": "😕 Non riesco a leggere il prezzo da questo link",
        "track_bad_target": "La soglia dev'essere un numero positivo. Esempio: /track <link> 130",
        "track_found": "✅ Trovato «{name}» a {price}{currency}. Manda la soglia (es. 130) sotto cui avvisarti, oppure /skip per seguirlo senza soglia.",
        "track_limit": "⚠️ Hai raggiunto il limite di {max} prodotti seguiti: rimuovine qualcuno con /untrack.",
        "display_tracked": "Ecco la lista dei prodotti seguiti:\n{items}",
        "last_price": "ultimo prezzo",
        "target": "soglia",
        "empty_list": "Non sono presenti prodotti seguiti!",
        "missing_id": "Inserire l'id del prodotto!",
        "product_not_tracked": "Il prodotto {id} non è seguito!",
        "id_error": "Errore! L'id non è valido!",
        "untrack_ok": "✅ Il prodotto {id} è stato rimosso dalla watch list!",
        "price_drop": "📉 Il prezzo di «{name}» è sceso da {old}{currency} a {new}{currency}!\n{url}",
        "check_broken": "⚠️ Non riesco più a leggere il prezzo di «{name}». Continuerò a riprovare!",
        "missing_values": "Non sono presenti valori per il prodotto {id}",
        "display_history": (
            "Prezzi registrati per «{name}»: \n{items}\n"
            "Media: {mean} €\n\n{url}"
        ),
        "cmd_track": "Aggiungi un prodotto da monitorare",
        "cmd_list": "Mostra i prodotti che segui",
        "cmd_untrack": "Smetti di seguire un prodotto",
        "cmd_history": "Ottieni lo storico di un prodotto",
        "cmd_set_target": "Imposta la soglia di un prodotto",
        "cmd_reset_target": "Rimuovi la soglia di un prodotto",
        "ask_target_price": "A che prezzo vuoi impostare la soglia?",
        "target_removed": "✅ Soglia rimossa per «{name}».",
        "target_updated": "✅ Nuova soglia per «{name}»: {target}€",
        "cancelled": "❌ Operazione annullata.",
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
            "/show_history <id> — show a product's price history\n"
            "/set_target <id> <price> — set/update a product's target price\n"
            "/reset_target <id> — remove a product's target price"
        ),
        "track_usage": "Usage: /track <Amazon link> [price]",
        "track_unsupported": "For now I only track Amazon links. 🙈",
        "track_ok": "✅ Now tracking «{name}» at {price}{currency}. I'll let you know when it drops!",
        "track_ok_target": "✅ Now tracking «{name}» at {price}{currency}. I'll alert you when it drops below {target}{currency}!",
        "track_error": "😕 I couldn't read the price from this link",
        "track_bad_target": "The threshold must be a positive number. Example: /track <link> 130",
        "track_found": "✅ Found «{name}» at {price}{currency}. Send the target price (e.g. 130) to be alerted below it, or /skip to track it with no threshold.",
        "track_limit": "⚠️ You've reached the limit of {max} tracked products: remove some with /untrack.",
        "display_tracked": "Here are the products you follow:\n{items}",
        "last_price": "last price",
        "target": "target",
        "empty_list": "You are not following any product yet!",
        "missing_id": "Insert the id of the product!",
        "product_not_tracked": "The product {id} is not tracked!",
        "id_error": "Error! The id is not valid!",
        "untrack_ok": "✅ The product {id} has been removed from the watch list!",
        "price_drop": "📉 The price of «{name}» dropped from {old}{currency} to {new}{currency}!\n{url}",
        "check_broken": "⚠️ I can no longer read the price of «{name}». I'll keep trying!",
        "missing_values": "No records are available for product {id}",
        "display_history": (
            "Recorded prices for «{name}»: \n{items}\n"
            "Mean: {mean} €\n\n{url}"
        ),
        "cmd_track": "Add a product to monitor",
        "cmd_list": "Show the products you follow",
        "cmd_untrack": "Stop following a product",
        "cmd_history": "Get a product's price history",
        "cmd_set_target": "Set a product's target price",
        "cmd_reset_target": "Remove a product's target price",
        "ask_target_price": "What price do you want to set as the target?",
        "target_removed": "✅ Target removed for «{name}».",
        "target_updated": "✅ New target for «{name}»: {target}€",
        "cancelled": "❌ Cancelled.",
    },
}


def translate(key: str, lang: str | None, **kwargs) -> str:
    lang = (lang or DEFAULT_LANG).split("-")[0]
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return text.format(**kwargs)
