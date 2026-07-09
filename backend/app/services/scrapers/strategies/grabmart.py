# backend/app/services/scrapers/strategies/grabmart.py
from typing import Dict, Any
from app.services.scrapers.base import BaseScraper

class GrabMartScraper(BaseScraper):
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        return {}

    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {}
