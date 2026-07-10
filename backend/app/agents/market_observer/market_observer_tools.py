from typing import Dict

from sqlalchemy.orm import Session

from app.db import models
from app.scraper.scraper_engine import run_scraper_for_all_products


def refresh_market_prices(db: Session) -> Dict[int, list]:
    return run_scraper_for_all_products(db)


def get_latest_clean_competitor_price(db: Session, product_id: int):
    return (
        db.query(models.CompetitorPrice)
        .filter(
            models.CompetitorPrice.product_id == product_id,
            models.CompetitorPrice.stock_status != "OUT_OF_STOCK",
            models.CompetitorPrice.net_price.isnot(None),
            models.CompetitorPrice.is_suspicious == False,
        )
        .order_by(models.CompetitorPrice.scraped_at.desc())
        .first()
    )
