from urllib import parse
import requests
from bs4 import BeautifulSoup
from scrapers.base import Scraper
from core.models import ScrapeResult

DOMAINS = ['amazon', 'amzn']

USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9"
}

CURRENCY = {
    "€": "EUR",
    "£": "GBP",
    "$": "USD",
}


class AmazonScraper(Scraper):

    def can_handle(self, url: str) -> bool:
        domain = parse.urlparse(url).netloc.split(".")
        return any(d in DOMAINS for d in domain)

    def fetch(self, url: str) -> ScrapeResult:
        response = requests.get(url=url, timeout=10, headers=USER_AGENT)
        response.raise_for_status()

        data = BeautifulSoup(response.text, "lxml")

        name_el = data.select_one("#productTitle")
        price_el = data.select_one(".a-price .a-offscreen")
        symbol_el = data.select_one(".a-price-symbol")
        if name_el is None or price_el is None or symbol_el is None:
            raise ValueError("Pagina non riconosciuta: nome/prezzo/valuta non trovati")

        name = name_el.get_text().strip()
        price = self._extract_price(price_el.get_text())
        currency = self._get_currency(symbol_el.get_text())
        return ScrapeResult(name, price, currency)

    def _extract_price(self, text: str) -> float:
        cleaned = "".join(text.split())
        for symbol in CURRENCY:
            cleaned = cleaned.replace(symbol, "")
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)

    def _get_currency(self, text: str) -> str:
        symbol = text.strip()
        if symbol not in CURRENCY:
            raise ValueError(f"Valuta sconosciuta: {symbol!r}")
        return CURRENCY[symbol]
