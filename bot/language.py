DEFAULT_LANG = "en"

MESSAGES = {
    "it": {
        "welcome": (
            "Ciao {name}! 👋\n\n"
            "Monitoro i prezzi dei prodotti e ti avviso quando scendono.\n"
            "⚠️ Per ora funziono solo con link Amazon.\n\n"
            "📄 Comandi disponibili:\n"
            "/track <url> — aggiunge un prodotto alla watch list\n"
            "/list — mostra i prodotti che segui\n"
            "/untrack <id> — smette di seguire un prodotto"
        ),
        "track_usage": "Uso: /track <link Amazon>",
        "track_unsupported": "Per ora seguo solo link Amazon. 🙈",
        "track_ok": "✅ Ora seguo «{name}» a {price}€. Ti avviso quando scende!",
        "track_ok_target": "✅ Ora seguo «{name}» a {price}€. Ti avviso quando scende sotto {target}€!",
        "track_error": "😕 Non riesco a leggere il prezzo da questo link",
        "track_bad_target": "La soglia dev'essere un numero. Esempio: /track <link> 130",
        "display_tracked": "Ecco la lista dei prodotti seguiti:\n{products}",
        "empty_list": "Non sono presenti prodotti seguiti!",
        "missing_id_untrack": "Inserire l'id del prodotto da rimuovere dalla watch list",
        "missing_product_untrack": "Il prodotto {id} non è seguito!",
        "id_untrack_error": "Errore! L'id non è valido!",
        "untrack_ok": "✅ Il prodotto {id} è stato rimosso dalla watch list!",
        "price_drop": "📉 Il prezzo di «{name}» è sceso da {old}€ a {new}€!",
    },
    "en": {
        "welcome": (
            "Hi {name}! 👋\n\n"
            "I track product prices and alert you when they drop.\n"
            "⚠️ For now I only work with Amazon links.\n\n"
            "📄 Available commands:\n"
            "/track <url> — add a product to your watch list\n"
            "/list — show the products you follow\n"
            "/untrack <id> — stop following a product"
        ),
        "track_usage": "Usage: /track <Amazon link>",
        "track_unsupported": "For now I only track Amazon links. 🙈",
        "track_ok": "✅ Now tracking «{name}» at {price}€. I'll let you know when it drops!",
        "track_ok_target": "✅ Now tracking «{name}» at {price}€. I'll alert you when it drops below {target}€!",
        "track_error": "😕 I couldn't read the price from this link",
        "track_bad_target": "The threshold must be a number. Example: /track <link> 130",
        "display_tracked": "Here are the products you follow:\n{products}",
        "empty_list": "You are not following any product yet!",
        "missing_id_untrack": "Insert the id of the product to remove from the watch list",
        "missing_product_untrack": "The product {id} is not tracked!",
        "id_untrack_error": "Error! The id is not valid!",
        "untrack_ok": "✅ The product {id} has been removed from the watch list!",
        "price_drop": "📉 The price of «{name}» dropped from {old}€ to {new}€!",
    },
}


def translate(key: str, lang: str | None, **kwargs) -> str:
    lang = (lang or DEFAULT_LANG).split("-")[0]
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return text.format(**kwargs)
