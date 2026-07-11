# backend/app/services/scrapers/strategies/__init__.py
from app.services.scrapers.strategies.hasaki import HasakiScraper
from app.services.scrapers.strategies.pharmacity import PharmacityScraper
from app.services.scrapers.strategies.shopee import ShopeeScraper
from app.services.scrapers.strategies.lazada import LazadaScraper
from app.services.scrapers.strategies.tiktok import TikTokScraper
from app.services.scrapers.strategies.grabmart import GrabMartScraper

__all__ = [
    "HasakiScraper",
    "PharmacityScraper",
    "ShopeeScraper",
    "LazadaScraper",
    "TikTokScraper",
    "GrabMartScraper",
]
