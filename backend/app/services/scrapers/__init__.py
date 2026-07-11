# backend/app/services/scrapers/__init__.py
from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string
from app.services.scrapers.factory import ScraperFactory, SUPPORTED_PLATFORMS

__all__ = [
    "BaseScraper",
    "CompetitorPriceDTO",
    "clean_price_string",
    "ScraperFactory",
    "SUPPORTED_PLATFORMS",
]
