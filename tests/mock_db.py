import config

from core.models import House
from storage.database import init_db
from storage.repository import (
    add_houses,
    add_price,
    add_product,
    add_subscription,
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