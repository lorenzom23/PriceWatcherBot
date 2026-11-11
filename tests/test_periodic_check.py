from types import SimpleNamespace

import core.checker
from core.checker import check_all
from core.models import House
from mock_db import DATA_MOCKED, setup_db_with_data
from scrapers.sites.amazon import AmazonScraper
from scrapers.sites.immobiliare import ImmobiliareScraper
from storage.repository import get_houses


def test_immobiliare_check_all(monkeypatch, tmp_path):
    setup_db_with_data(tmp_path, monkeypatch)
    monkeypatch.setattr(core.checker, "MAX_PARALLEL_SITES", 1)  # per debug deterministico

    new_immobiliare_result = [
        House(id="house-4", price=180000.0, location="Turin"),
        House(id="house-6", price=300000.0, location="Florence"),  # drop price
        House(id="house-5", price=260000.0, location="Bologna"),
        House(id="house-7", price=400000.0, location="Venice"),    # drop price
        House(id="house-9", price=450000.0, location="Pisa"),      # new house
        House(id="house-8", price=490000.0, location="Genoa"),
    ]
    expected_result = [
        ("house_price_drop", DATA_MOCKED["chat_id"], {
            "location": DATA_MOCKED["immobiliare"][1]["houses"][2].location,
            "old": DATA_MOCKED["immobiliare"][1]["houses"][2].price,
            "new": new_immobiliare_result[1].price,
            "url": f"https://www.immobiliare.it/annunci/{DATA_MOCKED['immobiliare'][1]['houses'][2].id}",
        }),
        ("house_price_drop", DATA_MOCKED["chat_id"], {
            "location": DATA_MOCKED["immobiliare"][1]["houses"][3].location,
            "old": DATA_MOCKED["immobiliare"][1]["houses"][3].price,
            "new": new_immobiliare_result[3].price,
            "url": f"https://www.immobiliare.it/annunci/{DATA_MOCKED['immobiliare'][1]['houses'][3].id}",
        }),
        ("new_house", DATA_MOCKED["chat_id"], {
            "price": new_immobiliare_result[4].price,
            "location": new_immobiliare_result[4].location,
            "url": f"https://www.immobiliare.it/annunci/{new_immobiliare_result[4].id}",
        }),
    ]

    def mock_fetch_immobiliare(_scraper, url):
        if url == DATA_MOCKED["immobiliare"][0]["search_url"]:
            return DATA_MOCKED["immobiliare"][0]["houses"]
        assert url == DATA_MOCKED["immobiliare"][1]["search_url"]
        return new_immobiliare_result

    def mock_fetch_amazon(_scraper, url):
        product = next(item for item in DATA_MOCKED["amazon"] if item["url"] == url)
        return SimpleNamespace(name=product["name"], price=product["price"], currency="EUR")

    monkeypatch.setattr(ImmobiliareScraper, "fetch", mock_fetch_immobiliare)
    monkeypatch.setattr(AmazonScraper, "fetch", mock_fetch_amazon)
    monkeypatch.setattr("core.checker.time.sleep", lambda _seconds: None)

    result = check_all()
    assert result == expected_result

    stored_houses = [
        House(id, price, location)
        for id, price, location in get_houses(
            DATA_MOCKED["chat_id"], DATA_MOCKED["immobiliare"][1]["search_url"]
        )
    ]
    assert stored_houses == sorted(new_immobiliare_result, key=lambda house: house.id)
