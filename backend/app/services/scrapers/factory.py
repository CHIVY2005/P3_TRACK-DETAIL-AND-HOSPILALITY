# backend/app/services/scrapers/factory.py
from app.services.scrapers.base import BaseScraper
from app.services.scrapers.strategies.shopee import ShopeeScraper
from app.services.scrapers.strategies.hasaki import HasakiScraper
from app.services.scrapers.strategies.grabmart import GrabMartScraper

class ScraperFactory:
    @staticmethod
    def get_scraper(platform_name: str) -> BaseScraper:
        platform_name = platform_name.lower()
        if platform_name == "shopee":
            return ShopeeScraper()
        elif platform_name == "hasaki":
            return HasakiScraper()
        elif platform_name == "grabmart":
            return GrabMartScraper()
        else:
            raise ValueError(f"No scraper strategy found for platform: {platform_name}")
