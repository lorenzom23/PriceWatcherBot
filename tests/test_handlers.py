import asyncio
import config

from telegram.ext import ConversationHandler
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot import handlers
from bot.language import translate
from core.models import House
from storage.database import init_db
from storage.repository import (
    add_houses,
    add_price,
    add_product,
    add_subscription,
    get_houses,
    get_user_language,
    save_user,
)

DATA_MOCKED = {
    "chat_id": 3,
    "language": "it",
    "amazon": [
        {
            "url": "https://www.amazon.it/dp/mock-product",
            "name": "Mock Amazon product",
            "website": "www.amazon.it",
            "price": 199.0,
            "timestamp": "2026-10-01T00:00:00",
        },
        {
            "url": "https://www.amazon.it/dp/mock-headphones",
            "name": "Mock Amazon headphones",
            "website": "www.amazon.it",
            "price": 79.0,
            "timestamp": "2026-10-02T00:00:00",
        },
        {
            "url": "https://www.amazon.it/dp/mock-keyboard",
            "name": "Mock Amazon keyboard",
            "website": "www.amazon.it",
            "price": 49.0,
            "timestamp": "2026-10-03T00:00:00",
        },
    ],
    "immobiliare": [
        {
            "search_url": "https://www.immobiliare.it/ricerca/?criterio=rilevante&prezzoMassimo=300000&tipologiaContratto=1&tip",
            "houses": [
                House(id="house-1", price=150000.0, location="Milan"),
                House(id="house-2", price=220000.0, location="Rome"),
                House(id="house-3", price=310000.0, location="Naples"),
            ],
        },
        {
            "search_url": "https://www.immobiliare.it/ricerca/?idContratto=1&prezzoMassimo=500000",
            "houses": [
                House(id="house-4", price=180000.0, location="Turin"),
                House(id="house-5", price=260000.0, location="Bologna"),
                House(id="house-6", price=340000.0, location="Florence"),
                House(id="house-7", price=420000.0, location="Venice"),
                House(id="house-8", price=490000.0, location="Genoa"),
            ],
        },
    ],
}


class DummyTelegramMessage:
    ''' Simulates the behavior of a Telegram message for testing purposes.
        It captures the text sent in replies for later inspection.'''

    def __init__(self):
        self.reply_storage: list[str] = []

    async def reply_text(self, text):
        self.reply_storage.append(text)


class DummyTelegramUpdate:
    ''' Simulates the behavior of a Telegram update for testing purposes.
        It contains a message and user information, and captures replies sent to the user.'''

    def __init__(self, chat_id, lang="it", first_name="FigoMazzo"):
        self.effective_chat = SimpleNamespace(id=chat_id)
        self.effective_user = SimpleNamespace(language_code=lang, first_name=first_name)
        self.message = DummyTelegramMessage()


class DummyTelegramContext:
    def __init__(self, args=None):
        self.args = [] if args is None else args
        self.user_data = {}


# monkeypatch and tmp_path are pytest fixtures.
# - tmp_path provides a temporary directory for this test
# - monkeypatch lets the test replace values or functions temporarily.
def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", str(db_path))
    init_db()
    return db_path


def setup_db_with_data(tmp_path, monkeypatch):
    setup_db(tmp_path, monkeypatch)
    chat_id = DATA_MOCKED["chat_id"]
    save_user(chat_id, DATA_MOCKED["language"])
    product_ids = []
    for amazon in DATA_MOCKED["amazon"]:
        product_id, _ = add_product(amazon["url"], amazon["name"], amazon["website"])
        add_price(product_id, amazon["price"], amazon["timestamp"])
        add_subscription(chat_id, product_id)
        product_ids.append(product_id)

    for search in DATA_MOCKED["immobiliare"]:
        add_houses(chat_id, search["search_url"], search["houses"])
    return product_ids


def test_welcome_message(monkeypatch, tmp_path):
    setup_db(tmp_path, monkeypatch)
    user_name = "FigoMazzo"
    update = DummyTelegramUpdate(chat_id=5, first_name=user_name)
    context = DummyTelegramContext()
    asyncio.run(handlers.start(update, context))
    assert update.message.reply_storage[0] == translate("welcome", "it", name=user_name)
    # check user is saved in the db
    assert get_user_language(5) == "it"


def test_immobiliare_track(monkeypatch, tmp_path):
    setup_db(tmp_path, monkeypatch)
    chat_id = 1
    update = DummyTelegramUpdate(chat_id=chat_id)

    # url not provided, should ask for it
    context = DummyTelegramContext()
    res = asyncio.run(handlers.track(update, context))
    assert update.message.reply_storage[0] == translate("track_ask_url", "it")
    assert res == handlers.ConversationState.WAITING_URL

    # url provided but not supported
    url = "https://www.succhi.it/search-list/?idContratto=1"
    context = DummyTelegramContext(args=[url])
    res = asyncio.run(handlers.track(update, context))
    assert update.message.reply_storage[-1] == translate("track_unsupported", "it")
    assert res == ConversationHandler.END

    # url provided and supported, should fetch and save houses
    search = DATA_MOCKED["immobiliare"][0]
    url = search["search_url"]
    context = DummyTelegramContext(args=[url])

    fetch_mock = AsyncMock(return_value=search["houses"])
    monkeypatch.setattr(handlers.asyncio, "to_thread", fetch_mock)
    res = asyncio.run(handlers.track(update, context))
    assert res == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("track_houses_ok", "it", count=len(search["houses"]))
    db_houses = [House(id, price, location) for id, price, location in get_houses(chat_id, url)]
    assert db_houses == search["houses"]

    # track twice the same url, should block it
    res = asyncio.run(handlers.track(update, context))
    assert res == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("track_houses_existing",
                                                         "it", count=len(search["houses"]))


def test_immobiliare_track_receive_url(monkeypatch, tmp_path):
    setup_db(tmp_path, monkeypatch)
    chat_id = 2
    update = DummyTelegramUpdate(chat_id=chat_id)

    # url not supported
    context = DummyTelegramContext()
    update.message.text = "https://www.succhi.it/search-list/?idContratto=1"
    result = asyncio.run(handlers.track_receive_url(update, context))
    assert result == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("track_unsupported", "it")

    # url supported, should fetch and save houses
    search = DATA_MOCKED["immobiliare"][0]
    url = search["search_url"]
    fetch_mock = AsyncMock(return_value=search["houses"])
    monkeypatch.setattr(handlers.asyncio, "to_thread", fetch_mock)
    update.message.text = url

    result = asyncio.run(handlers.track_receive_url(update, context))

    assert result == ConversationHandler.END
    assert fetch_mock.await_count == 1
    assert update.message.reply_storage[-1] == translate(
        "track_houses_ok", "it", count=len(search["houses"])
    )
    db_houses = [House(id, price, location) for id, price, location in get_houses(chat_id, url)]
    assert db_houses == search["houses"]


def test_immobiliare_untrack(monkeypatch, tmp_path):
    # empty db
    setup_db(tmp_path, monkeypatch)
    context = DummyTelegramContext()
    update = DummyTelegramUpdate(chat_id=DATA_MOCKED["chat_id"])
    result = asyncio.run(handlers.untrack(update, context))
    assert result == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("empty_list", "it")

    # db with data
    product_ids = setup_db_with_data(tmp_path, monkeypatch)

    # no untrack id provided
    result = asyncio.run(handlers.untrack(update, context))
    assert result == handlers.ConversationState.SELECT_UNTRACK_ID

    # untrack id provided, but wrong format
    context = DummyTelegramContext(args=["abc"])
    result = asyncio.run(handlers.untrack(update, context))
    assert result == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("id_error", "it")

    # untrack id provided correctly but out of range
    context = DummyTelegramContext(args=["999"])
    result = asyncio.run(handlers.untrack(update, context))
    assert result == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("id_error", "it")

   # untrack id provided correctly and in range
    context = DummyTelegramContext(args=["4"])  # untrack the first Immobiliare search
    result = asyncio.run(handlers.untrack(update, context))
    assert result == ConversationHandler.END
    assert update.message.reply_storage[-1] == translate("untrack_ok", "it", id=4)
    houses = get_houses(DATA_MOCKED["chat_id"], DATA_MOCKED["immobiliare"][0]["search_url"])
    assert houses == []
