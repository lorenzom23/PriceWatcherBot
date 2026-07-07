from core.models import ScrapeResult
from abc import ABC, abstractmethod


class ScrapeBlocked(Exception):
    """The site replied with an anti-bot page instead of the product page."""


class Scraper(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str) -> ScrapeResult:
        pass
