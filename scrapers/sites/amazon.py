import re
import random
from urllib import parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from scrapers.base import Scraper, ScrapeBlocked
from core.models import ScrapeResult

DOMAINS = ['amazon', 'amzn']

# suffissi non pubblici: "amazon.localhost" risolve in loopback → SSRF
PRIVATE_TLDS = {"localhost", "local", "internal", "lan", "home", "corp"}

# UA reali e correnti: uno fisso è il fingerprint più facile da bloccare
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

CURRENCY = {
    "€": "EUR",
    "£": "GBP",
    "$": "USD",
}

PRICE_SELECTORS = [
    "#corePrice_feature_div .a-offscreen",
    ".a-price:not(.a-text-price) .a-offscreen",
]


class AmazonScraper(Scraper):

    def can_handle(self, url: str) -> bool:
        labels = (parse.urlparse(url).hostname or "").split(".")
        if len(labels) < 2 or labels[-1] in PRIVATE_TLDS:
            return False
        # match sul dominio registrato (amazon.it, www.amazon.co.uk, amzn.to),
        # non su un label qualsiasi: amazon.evil.com non deve passare
        # ponytail: senza public-suffix-list resta il caso "co.<tld>" registrato ad hoc, accettabile qui
        sld = labels[-2]
        if sld in ("co", "com") and len(labels) >= 3:
            sld = labels[-3]
        return sld in DOMAINS

    def fetch(self, url: str) -> ScrapeResult:
        session = requests.Session()
        # riprova su errori di rete e 5xx (Amazon usa spesso 503 per il rate limiting)
        adapter = HTTPAdapter(max_retries=Retry(
            total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504]))
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        # redirect seguiti a mano, ogni hop validato PRIMA della richiesta: altrimenti un open
        # redirect su un dominio amazon (o un amzn.to ad arte) fa uscire la GET verso host
        # arbitrari, anche nella LAN (SSRF)
        response = session.get(url=url, timeout=10, headers=_headers(), allow_redirects=False)
        for _ in range(5):
            if not response.is_redirect:
                break
            next_url = parse.urljoin(response.url, response.headers["location"])
            if not self.can_handle(next_url):
                raise ValueError(f"Redirect fuori dominio: {next_url}")
            response = session.get(url=next_url, timeout=10, headers=_headers(), allow_redirects=False)
        if response.is_redirect:
            raise ValueError("Troppi redirect")
        response.raise_for_status()

        data = BeautifulSoup(response.text, "lxml")

        # Amazon risponde 200 con la robot page: non è un cambio di layout
        if data.select_one("#captchacharacters") or "api-services-support@amazon.com" in response.text:
            raise ScrapeBlocked("Amazon ha risposto con la pagina anti-bot")

        name_el = data.select_one("#productTitle")
        symbol_el = data.select_one(".a-price-symbol")

        price_text = self._find_price(data)

        if name_el is None or price_text is None or symbol_el is None:
            raise ValueError("Pagina non riconosciuta: nome/prezzo/valuta non trovati")

        name = name_el.get_text().strip()
        price = self._extract_price(price_text)
        currency = self._get_currency(symbol_el.get_text())
        return ScrapeResult(name, price, currency)

    def _find_price(self, data) -> str | None:
        for selector in PRICE_SELECTORS:
            for el in data.select(selector):
                if el.get_text().strip():
                    return el.get_text()
        return None

    def _extract_price(self, text: str) -> float:
        # keep only digits and separators (strips currency symbols, spaces, NBSP…)
        cleaned = re.sub(r"[^\d.,]", "", text)
        if "," in cleaned and "." in cleaned:
            # both present: the rightmost separator is the decimal one
            decimal = "," if cleaned.rfind(",") > cleaned.rfind(".") else "."
            thousands = "." if decimal == "," else ","
            cleaned = cleaned.replace(thousands, "").replace(decimal, ".")
        elif "," in cleaned:
            # single sep: decimal if it groups 1-2 trailing digits, else thousands
            cleaned = cleaned.replace(",", "." if len(cleaned.rsplit(",", 1)[-1]) <= 2 else "")
        elif "." in cleaned:
            # ponytail: 3 trailing digits ⇒ thousands sep; a genuine 3-decimal price would
            # misparse, but retail currency prices have ≤2 decimals
            cleaned = cleaned.replace(".", "" if len(cleaned.rsplit(".", 1)[-1]) == 3 else ".")
        return float(cleaned)

    def _get_currency(self, text: str) -> str:
        symbol = text.strip()
        if symbol not in CURRENCY:
            raise ValueError(f"Valuta sconosciuta: {symbol!r}")
        return CURRENCY[symbol]
