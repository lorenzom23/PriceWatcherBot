DEFAULT_LANG = "en"

MESSAGES = {
    "it": {
        "welcome": (
            "Ciao {name}! 👋\n\n"
            "Monitoro i prezzi dei prodotti e ti avviso quando scendono.\n"
            "⚠️ Per ora funziono solo con link Amazon."
        ),
    },
    "en": {
        "welcome": (
            "Hi {name}! 👋\n\n"
            "I track product prices and alert you when they drop.\n"
            "⚠️ For now I only work with Amazon links."
        ),
    },
}


def translate(key: str, lang: str | None, **kwargs) -> str:
    lang = (lang or DEFAULT_LANG).split("-")[0]
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG].get(key) or key
    return text.format(**kwargs)
