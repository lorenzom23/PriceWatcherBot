from core.models import ScrapeResult
from abc import ABC, abstractmethod

class Scraper(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    def fetch(self, url: str) -> ScrapeResult:
        pass
