DEFAULT_LANG = "en"

MESSAGES = {
    "it": {
        "welcome": (
            "Ciao {name}! 👋\n\n"
            "Monitoro i prezzi dei prodotti e ti avviso quando scendono.\n"
            "⚠️ Per ora funziono solo con link Amazon.\n\n"
            "📄 Comandi disponibili:\n"
            "/track <url> — aggiunge un prodotto alla watch list"
        ),
        "track_usage": "Uso: /track <link Amazon>",
        "track_unsupported": "Per ora seguo solo link Amazon. 🙈",
        "track_ok": "✅ Ora seguo «{name}» a {price}€. Ti avviso quando scende!",
    },
    "en": {
        "welcome": (
            "Hi {name}! 👋\n\n"
            "I track product prices and alert you when they drop.\n"
            "⚠️ For now I only work with Amazon links.\n\n"
            "📄 Available commands:\n"
            "/track <url> — add a product to your watch list"
        ),
        "track_usage": "Usage: /track <Amazon link>",
        "track_unsupported": "For now I only track Amazon links. 🙈",
        "track_ok": "✅ Now tracking «{name}» at {price}€. I'll let you know when it drops!",
    },
}


def translate(key: str, lang: str | None, **kwargs) -> str:
    lang = (lang or DEFAULT_LANG).split("-")[0]
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return text.format(**kwargs)
