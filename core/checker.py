import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import config
from scrapers.base import ScrapeBlocked, Scraper
from scrapers.sites.immobiliare import ImmobiliareScraper
from scrapers.registry import get_scraper
from storage.repository import (
    get_house_searches, get_subscribers, get_last_price, add_price, get_tracked_products,
    record_check_failure, reset_check_failures, prune_history, update_product_name,
    get_houses, upsert_houses
)
from core.models import House
from logger import logger

FAILURE_ALERT_THRESHOLD = 3  # con un check ogni 6h ≈ 18h di fallimenti prima di avvisare
MAX_PARALLEL_SITES = 4  # gira su un Raspberry Pi: pochi thread bastano


def check_product(scraper: Scraper, id, url) -> list:
    result = scraper.fetch(url)
    alerts = []
    if isinstance(scraper, ImmobiliareScraper):
        chat_id = id
        new_houses: list[House] = result
        houses_to_upsert = []
        db_houses = {house_id: price
                     for house_id, price, _ in get_houses(chat_id, url)}
        for new_house in new_houses:
            house_url = f"https://www.immobiliare.it/annunci/{new_house.id}"
            if new_house.id not in db_houses:
                alerts.append((
                    "new_house", chat_id,
                    {
                        "price": new_house.price,
                        "location": new_house.location,
                        "url": house_url
                    }))
                houses_to_upsert.append(new_house)
            else:
                old_price = db_houses[new_house.id]
                if new_house.price < old_price:
                    alerts.append((
                        "house_price_drop", chat_id,
                        {
                            "location": new_house.location,
                            "old": old_price,
                            "new": new_house.price,
                            "url": house_url
                        }))
                    houses_to_upsert.append(new_house)
        if houses_to_upsert:
            upsert_houses(chat_id, url, houses_to_upsert)
        logger.info("Finished checking Immobiliare.it for chat %s: %d alerts", chat_id, len(alerts))
    else:
        product_id = id
        last_price = get_last_price(product_id)
        update_product_name(product_id, result.name)  # Amazon rinomina i listing: /list non deve mostrare titoli vecchi
        add_price(product_id, result.price, datetime.now().isoformat())

        if not last_price or result.price >= last_price:
            return []

        for chat_id, target in get_subscribers(product_id):
            if target is None or result.price <= target:
                alerts.append((
                    "price_drop", chat_id,
                    {
                        "name": result.name,
                        "old": last_price,
                        "new": result.price,
                        "currency": result.currency,
                        "url": url
                    }))
        logger.info("Finished checking %s: %d alerts", result.name, len(alerts))
    return alerts


def _record_failure(product_id, product_name, out):
    if record_check_failure(product_id) == FAILURE_ALERT_THRESHOLD:
        # avvisa una volta sola, poi continua a riprovare in silenzio
        out.extend(("check_broken", chat_id, {"name": product_name})
                   for chat_id, _ in get_subscribers(product_id))


def _check_batch(scraper: Scraper, batch) -> list:
    """Controlla in sequenza (con jitter) i prodotti di un singolo sito."""
    result = []
    for i, (id, product_url, product_name) in enumerate(batch):
        time.sleep(random.uniform(2, 5))  # jitter: niente richieste a raffica
        try:
            alerts = check_product(scraper, id, product_url)
        except Exception:
            kind = "Anti-bot" if isinstance(e, ScrapeBlocked) else "Errore"
            logger.exception("%s su %s", kind, product_url)
            _record_failure(id, product_name, result)
            if isinstance(e, ScrapeBlocked):
                # il sito ci ha bloccato: insistere peggiora il ban, si riprova al giro dopo.
                # Anche i prodotti saltati contano il fallimento: il loro check_broken deve
                # maturare, non solo quello del primo prodotto del batch
                for skipped_id, _, skipped_name in batch[i + 1:]:
                    _record_failure(skipped_id, skipped_name, result)
                break
            continue
        reset_check_failures(id)
        result.extend(alerts)
    return result


def check_all() -> list:
    """Returns (message_key, chat_id, params) tuples, ready for translate()"""
    prune_history((datetime.now() - timedelta(days=config.HISTORY_RETENTION_DAYS)).isoformat())

    # un batch per scraper: sequenziale (col jitter) dentro un sito, parallelo tra siti
    batches = defaultdict(list)
    house_searches = get_house_searches()
    products = get_tracked_products()
    tracked_list = [(p[0], p[1], p[2]) for p in products] + [(h[0], h[1], None) for h in house_searches]
    for item in tracked_list:
        try:
            key = get_scraper(item[1])
        except ValueError:
            key = None  # nessuno scraper: check_product fallirà e conterà il fallimento, come prima
        batches[key].append(item)

    if not batches:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_SITES, len(batches))) as pool:
        return [msg for alerts in pool.map(_check_batch, batches.keys(), batches.values()) for msg in alerts]
