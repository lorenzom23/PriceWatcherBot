import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import config
from scrapers.base import ScrapeBlocked
from scrapers.registry import get_scraper
from storage.repository import (
    get_subscribers, get_last_price, add_price, get_tracked_products,
    record_check_failure, reset_check_failures, prune_history, update_product_name
)

FAILURE_ALERT_THRESHOLD = 3  # con un check ogni 6h ≈ 18h di fallimenti prima di avvisare
MAX_PARALLEL_SITES = 4  # gira su un Raspberry Pi: pochi thread bastano

def check_product(product_id, url) -> list:
    scraper = get_scraper(url)
    last_price = get_last_price(product_id)

    result = scraper.fetch(url)
    update_product_name(product_id, result.name)  # Amazon rinomina i listing: /list non deve mostrare titoli vecchi
    add_price(product_id, result.price, datetime.now().isoformat())

    if not last_price or result.price >= last_price:
        return []

    alerts = []
    for chat_id, target in get_subscribers(product_id):
        if target is None or result.price <= target:
            alerts.append((chat_id, result.name, last_price, result.price, result.currency, url))
    return alerts

def _record_failure(product_id, product_name, out):
    if record_check_failure(product_id) == FAILURE_ALERT_THRESHOLD:
        # avvisa una volta sola, poi continua a riprovare in silenzio
        out.extend(("check_broken", chat_id, {"name": product_name})
                   for chat_id, _ in get_subscribers(product_id))

def _check_batch(products) -> list:
    """Controlla in sequenza (con jitter) i prodotti di un singolo sito."""
    result = []
    for i, (product_id, product_url, product_name) in enumerate(products):
        time.sleep(random.uniform(2, 5))  # jitter: niente richieste a raffica
        try:
            alerts = check_product(product_id, product_url)
        except Exception as e:
            kind = "Anti-bot" if isinstance(e, ScrapeBlocked) else "Errore"
            print(f"{kind} su {product_url}: {e}")
            _record_failure(product_id, product_name, result)
            if isinstance(e, ScrapeBlocked):
                # il sito ci ha bloccato: insistere peggiora il ban, si riprova al giro dopo.
                # Anche i prodotti saltati contano il fallimento: il loro check_broken deve
                # maturare, non solo quello del primo prodotto del batch
                for skipped_id, _, skipped_name in products[i + 1:]:
                    _record_failure(skipped_id, skipped_name, result)
                break
            continue
        reset_check_failures(product_id)
        result.extend(("price_drop", chat_id, {"name": name, "old": old, "new": new, "currency": cur, "url": url})
                      for chat_id, name, old, new, cur, url in alerts)
    return result

def check_all() -> list:
    """Returns (message_key, chat_id, params) tuples, ready for translate()"""
    prune_history((datetime.now() - timedelta(days=config.HISTORY_RETENTION_DAYS)).isoformat())

    # un batch per scraper: sequenziale (col jitter) dentro un sito, parallelo tra siti
    batches = defaultdict(list)
    for product in get_tracked_products():
        try:
            key = get_scraper(product[1])
        except ValueError:
            key = None  # nessuno scraper: check_product fallirà e conterà il fallimento, come prima
        batches[key].append(product)

    if not batches:
        return []
    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_SITES, len(batches))) as pool:
        return [msg for batch in pool.map(_check_batch, batches.values()) for msg in batch]
