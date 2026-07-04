import pkgutil
import importlib
import inspect

from scrapers.base import Scraper
from scrapers import sites


def _discover() -> list[Scraper]:
    """Scan the scrapers"""
    found = []
    for module_info in pkgutil.iter_modules(sites.__path__):
        module = importlib.import_module(f"scrapers.sites.{module_info.name}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, Scraper)
                and not inspect.isabstract(obj)
                and obj.__module__ == module.__name__
            ):
                found.append(obj())
    return found


SCRAPERS = _discover()
def get_scraper(url) -> Scraper:
    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper
    raise ValueError(f"Nessuno scraper per: {url}")
