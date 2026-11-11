import re
import time
import requests
from urllib import parse
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core.models import House
from logger import logger
from scrapers.base import Scraper
from config import PROXY_PORT, PROXY_RESPONSE_TIMEOUT, PROXY_URL, PROXY_TIMEOUT


LISTING_PATH = re.compile(r"^/annunci/(\d+)/?$")


class ImmobiliareScraper(Scraper):

    @staticmethod
    def _extract_price(text: str) -> float | None:
        match = re.search(r"(?:da\s*)?€\s*([\d.]+(?:,\d+)?)", text, re.IGNORECASE)
        if not match:
            return None
        return float(match.group(1).replace(".", "").replace(",", "."))

    def can_handle(self, url: str) -> bool:
        hostname = (parse.urlparse(url).hostname or "").lower().rstrip(".")
        return hostname == "immobiliare.it" or hostname.endswith(".immobiliare.it")

    def fetch(self, url: str) -> list[House]:
        logger.debug("Fetching Immobiliare.it URL: %s", url)
        if not self.can_handle(url):
            raise ValueError(f"URL non supportato: {url}")
        page_url = url
        houses: list[House] = []
        last_page = False
        i = 1
        while not last_page:
            logger.debug("Fetching page %d: %s", i, page_url)
            response = requests.post(
                url=f"{PROXY_URL}:{PROXY_PORT}/v1",
                json={"cmd": "request.get", "url": page_url, "maxTimeout": PROXY_TIMEOUT},
                timeout=PROXY_RESPONSE_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
            html = payload.get("solution", {}).get("response")
            if not isinstance(html, str) or not html:
                raise ValueError("Byparr non ha restituito HTML")
            houses_found = self._parse_houses(html)
            houses.extend(houses_found)
            next_link = self._find_next_page_link(html)
            if not next_link:
                last_page = True
            else:
                page_url = next_link
                time.sleep(5)
            i += 1
        if not houses:
            raise ValueError("Nessuna casa trovata")
        logger.info("Finito fetch di Immobiliare.it: %d case trovate", len(houses))
        return houses

    def _find_next_page_link(self, html: str) -> str | None:
        soup = BeautifulSoup(html, "lxml")
        next_link = soup.select_one('div[data-cy="pagination-next"] a[href]')
        if next_link:
            return urljoin("https://www.immobiliare.it", next_link["href"])
        return None

    def _parse_houses(self, html: str) -> list[House]:
        soup = BeautifulSoup(html, "lxml")
        houses = []
        listing_items = soup.select("ul[class*='Results_results__'] > li[class*='ListItem_item__']")
        if listing_items:
            for item in listing_items:
                house_id = item.get("id")
                price_element = item.select_one("div[class*='Price_price__'] span")
                price = self._extract_price(price_element.get_text(" ", strip=True)) if price_element else None
                title_element = item.select_one("a[class*='Title_title__']")
                title = title_element.get_text(" ", strip=True) if title_element else None
                if house_id is None or title is None or price is None:
                    logger.warning(
                        "Annuncio incompleto: id=%s, title=%s, price=%s",
                        house_id, title, price,
                    )
                    continue
                houses.append(House(house_id, price, title))
        else:
            logger.warning("Lista di case non trovata")
        return houses
