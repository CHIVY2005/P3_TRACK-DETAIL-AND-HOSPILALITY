# backend/app/services/scrapers/factory.py
"""
Factory Pattern — resolves the correct scraper strategy from platform name.

Provider Swap Architecture:
    The factory returns a BaseScraper whose `fetch_raw_json` hits Apify by default.
    To swap to BrightData or ZenRows in the future:
      1. Set env var  SCRAPER_PROVIDER=brightdata  (or zenrows)
      2. Create  strategies/providers/brightdata.py  inheriting from the platform scraper
         and overriding only `fetch_raw_json`.
    Since `parse_to_dto` is pure business-logic, it stays untouched.
"""
from __future__ import annotations

import os
from typing import Dict, Type

from app.services.scrapers.base import BaseScraper
from app.services.scrapers.strategies.shopee import ShopeeScraper
from app.services.scrapers.strategies.lazada import LazadaScraper
from app.services.scrapers.strategies.tiktok import TikTokScraper
from app.services.scrapers.strategies.hasaki import HasakiScraper
from app.services.scrapers.strategies.pharmacity import PharmacityScraper
from app.services.scrapers.strategies.grabmart import GrabMartScraper

# Registry — maps platform name → scraper class
_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "shopee": ShopeeScraper,
    "lazada": LazadaScraper,
    "tiktok": TikTokScraper,
    "tiktok_shop": TikTokScraper,
    "grabmart": GrabMartScraper,
    "hasaki": HasakiScraper,
    "pharmacity": PharmacityScraper,
}

# All supported platform names (used in bulk sync to iterate)
SUPPORTED_PLATFORMS = list(_REGISTRY.keys())


class ScraperFactory:
    """
    Resolves platform → BaseScraper instance.

    Usage:
        scraper = ScraperFactory.get_scraper("hasaki")
        dtos = scraper.parse_to_dto(raw_items, barcode="7612345678901")
    """

    @staticmethod
    def get_scraper(platform_name: str) -> BaseScraper:
        key = platform_name.lower().strip().replace(" ", "_")
        scraper_cls = _REGISTRY.get(key)
        if scraper_cls is None:
            raise ValueError(
                f"No scraper strategy for platform '{platform_name}'. "
                f"Supported: {', '.join(_REGISTRY.keys())}"
            )
        return scraper_cls()

    @staticmethod
    def get_all_scrapers() -> Dict[str, BaseScraper]:
        """Return an instance for every registered platform."""
        return {name: cls() for name, cls in _REGISTRY.items()}

    @staticmethod
    def register(platform_name: str, scraper_cls: Type[BaseScraper]) -> None:
        """
        Dynamically register a new platform scraper at runtime.
        Useful for plugins or provider-swap modules.
        """
        _REGISTRY[platform_name.lower().strip()] = scraper_cls
