from typing import Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.db import models
from app.scraper.scraper_engine import run_scraper_for_all_products
from app.services.channel_intelligence import get_latest_channel_observations


def refresh_market_prices(
    db: Session,
    progress_callback: Optional[Callable] = None,
) -> Dict[int, list]:
    return run_scraper_for_all_products(db, progress_callback=progress_callback)


def is_clean_price(row: models.CompetitorPrice) -> bool:
    """Pure predicate: is this observation usable as a market reference?"""
    return bool(
        row.net_price is not None
        and row.net_price > 0
        and not row.is_suspicious
        and (row.stock_status or "").replace("_", "").upper() not in {"OUTOFSTOCK", "OOS", "UNAVAILABLE"}
    )


def get_latest_clean_competitor_prices(db: Session, product_id: int):
    observations = get_latest_channel_observations(db, product_id=product_id)
    return [row for row in observations if is_clean_price(row)]


def select_reference_price(prices, product: models.Product, alert_type: str):
    """Pure selection: pick the most decision-relevant price from an already-clean list."""
    if not prices:
        return None

    if alert_type == "Underpriced":
        prices_above_guardian = [row for row in prices if row.net_price > product.guardian_price]
        if prices_above_guardian:
            return min(prices_above_guardian, key=lambda row: (row.net_price, row.competitor_name))
        return max(prices, key=lambda row: (row.net_price, row.competitor_name))

    return min(prices, key=lambda row: (row.net_price, row.competitor_name))


def get_alert_reference_price(
    db: Session,
    product: models.Product,
    alert_type: str,
):
    """Pick the most decision-relevant clean latest price, not an arbitrary last row."""
    prices = get_latest_clean_competitor_prices(db, product.id)
    return select_reference_price(prices, product, alert_type)


def get_latest_clean_competitor_price(db: Session, product_id: int):
    """Compatibility helper returning the strongest current competitive reference."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    return get_alert_reference_price(db, product, "Competitor Undercutting") if product else None
