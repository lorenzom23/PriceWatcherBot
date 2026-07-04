from datetime import datetime
from dataclasses import dataclass

@dataclass
class ScrapeResult:
    name: str
    price: float
    currency: str

@dataclass
class Product:
    id: int
    url: str
    name: str
    website: str
    target_price: float | None = None

@dataclass
class PricePoint:
    product_id: int
    price: float
    timestamp: datetime
