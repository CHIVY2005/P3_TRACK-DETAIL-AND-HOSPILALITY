# backend/app/services/scrapers/base.py
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    @abstractmethod
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def get_fixture_fallback(self) -> Dict[str, Any]:
        """Centralized Fixture Fallback mechanism."""
        return {
            "platform": "Fallback",
            "title": "Mock Product (Fallback)",
            "current_price": 999999,
            "original_price": 999999,
            "promotion": None,
            "sku_platform": "000000",
            "hierarchy": "Fallback > Category",
            "url": "https://fallback.local",
            "stock_status": "Out of Stock",
            "rating": 0.0,
            "raw_data": {"fallback": True}
        }

    async def execute_pipeline(self, target_url: str) -> Dict[str, Any]:
        try:
            raw_data = await self.fetch_raw_json(target_url)
            return self.clean_data(raw_data)
        except Exception as e:
            logger.error(f"Scraping failed for {target_url}: {e}")
            return self.get_fixture_fallback()
