from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.scraper.scraper_engine import scrape_realtime_competitor_prices
from app.services.link_discovery import ensure_competitor_link

router = APIRouter()


class SyncResponse(BaseModel):
    status: str
    matched_product: Optional[Dict[str, Any]] = None
    updated_price: Optional[float] = None
    message: Optional[str] = None


@router.post("/sync-price/{barcode}", response_model=SyncResponse)
def sync_price(barcode: str, platform: str = "Hasaki", db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.barcode == barcode).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    link = ensure_competitor_link(db, product, platform)
    if not link:
        return SyncResponse(status="not_found", message=f"No discovery strategy configured for platform {platform}.")

    scrape_realtime_competitor_prices(db, product.id)
    latest_price = (
        db.query(models.CompetitorPrice)
        .filter(models.CompetitorPrice.product_id == product.id, models.CompetitorPrice.competitor_name == platform)
        .order_by(models.CompetitorPrice.scraped_at.desc())
        .first()
    )
    if not latest_price or latest_price.net_price is None:
        return SyncResponse(status="not_found", message="No valid price data captured for this platform.")

    return SyncResponse(
        status="success",
        matched_product={
            "product_id": product.id,
            "product_name": product.name,
            "platform": platform,
            "url": latest_price.url or link.url,
            "stock_status": latest_price.stock_status,
        },
        updated_price=latest_price.net_price,
        message="Price synchronization completed.",
    )
