from datetime import datetime
from scrapers.registry import get_scraper
from storage.repository import get_subscribers, get_last_price, add_price, get_all_products

def check_product(product_id, url) -> list:
    scraper = get_scraper(url)
    last_price = get_last_price(product_id)

    result = scraper.fetch(url)
    add_price(product_id, result.price, datetime.now().isoformat())

    if not last_price or result.price >= last_price:
        return []

    subscribers = get_subscribers(product_id)
    return [(sub[0], result.name, last_price, result.price) for sub in subscribers]

def check_all() -> list:
    result = []
    products = get_all_products()
    for (product_id, product_url) in products:
        try:
            result.extend(check_product(product_id, product_url))
        except Exception as e:
            print(f"Errore su {product_url}: {e}")
    return result
