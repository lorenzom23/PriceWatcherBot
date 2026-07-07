import random
import time
from datetime import datetime, timedelta
import config
from scrapers.base import ScrapeBlocked
from scrapers.registry import get_scraper
from storage.repository import (
    get_subscribers, get_last_price, add_price, get_tracked_products,
    record_check_failure, reset_check_failures, prune_history
)

FAILURE_ALERT_THRESHOLD = 3  # con un check ogni 6h ≈ 18h di fallimenti prima di avvisare

def check_product(product_id, url) -> list:
    scraper = get_scraper(url)
    last_price = get_last_price(product_id)

    result = scraper.fetch(url)
    add_price(product_id, result.price, datetime.now().isoformat())

    if not last_price or result.price >= last_price:
        return []

    alerts = []
    for chat_id, target in get_subscribers(product_id):
        if target is None or result.price <= target:
            alerts.append((chat_id, result.name, last_price, result.price))
    return alerts

def check_all() -> list:
    """Returns (message_key, chat_id, params) tuples, ready for translate()"""
    prune_history((datetime.now() - timedelta(days=config.HISTORY_RETENTION_DAYS)).isoformat())

    result = []
    products = get_tracked_products()
    for (product_id, product_url, product_name) in products:
        time.sleep(random.uniform(2, 5))  # jitter: niente richieste a raffica
        try:
            alerts = check_product(product_id, product_url)
        except Exception as e:
            kind = "Anti-bot" if isinstance(e, ScrapeBlocked) else "Errore"
            print(f"{kind} su {product_url}: {e}")
            if record_check_failure(product_id) == FAILURE_ALERT_THRESHOLD:
                # avvisa una volta sola, poi continua a riprovare in silenzio
                result.extend(("check_broken", chat_id, {"name": product_name})
                              for chat_id, _ in get_subscribers(product_id))
            continue
        reset_check_failures(product_id)
        result.extend(("price_drop", chat_id, {"name": name, "old": old, "new": new})
                      for chat_id, name, old, new in alerts)
    return result
