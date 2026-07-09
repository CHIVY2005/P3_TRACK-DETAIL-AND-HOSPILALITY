import re
import urllib.parse
from typing import Any, Dict, List, Optional

import asyncio
import random
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import CompetitorLink, PriceHistory, SkuMaster
from app.db.session import get_db
from app.services.apify_client import ApifyClientService, get_apify_service

router = APIRouter()


class SyncResponse(BaseModel):
    status: str
    matched_product: Optional[Dict[str, Any]] = None
    updated_price: Optional[float] = None
    message: Optional[str] = None


def parse_price_to_int(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return int(float(value))

    if isinstance(value, str):
        digits = re.sub(r"[^\d]", "", value.strip())
        if digits:
            return int(digits)

    return None


def normalize_scraper_item(raw_item: Dict[str, Any], fallback_platform: str) -> Optional[Dict[str, Any]]:
    if not raw_item or not isinstance(raw_item, dict):
        return None

    title = raw_item.get("title") or raw_item.get("name") or raw_item.get("product_title")
    current_price = parse_price_to_int(
        raw_item.get("current_price")
        if raw_item.get("current_price") is not None
        else raw_item.get("price")
    )
    original_price = parse_price_to_int(
        raw_item.get("original_price")
        if raw_item.get("original_price") is not None
        else raw_item.get("price_before_discount")
    )

    breadcrumbs = raw_item.get("breadcrumb") or raw_item.get("breadcrumbs") or []
    hierarchy = None
    if isinstance(breadcrumbs, list) and breadcrumbs:
        names = [crumb.get("name") for crumb in breadcrumbs if isinstance(crumb, dict) and crumb.get("name")]
        if names:
            hierarchy = " > ".join(names)

    if raw_item.get("url"):
        url = raw_item.get("url")
    elif isinstance(breadcrumbs, list) and breadcrumbs:
        last_crumb = breadcrumbs[-1] if isinstance(breadcrumbs[-1], dict) else {}
        url = last_crumb.get("url")
    else:
        item_id = raw_item.get("item_id") or raw_item.get("id") or raw_item.get("sku")
        shop_id = raw_item.get("shop_id") or raw_item.get("shopid")
        if item_id and shop_id and fallback_platform.lower() == "shopee":
            url = f"https://shopee.vn/product/{shop_id}/{item_id}"
        elif item_id:
            url = str(item_id)
        else:
            url = None

    discount_pct = raw_item.get("discount_pct")
    promotion = f"Giảm {discount_pct}%" if discount_pct not in (None, "", 0) else None

    sku_platform = raw_item.get("sku_platform") or raw_item.get("item_id") or raw_item.get("id") or raw_item.get("sku")

    normalized = {
        "platform": raw_item.get("platform") or fallback_platform,
        "title": title,
        "current_price": current_price,
        "original_price": original_price,
        "promotion": promotion,
        "sku_platform": str(sku_platform) if sku_platform is not None else None,
        "hierarchy": hierarchy,
        "url": url,
        "stock_status": raw_item.get("stock_status") or raw_item.get("availability"),
        "rating": raw_item.get("rating") or raw_item.get("rating_star"),
        "raw_data": raw_item,
    }

    return normalized if normalized["title"] else None


def select_first_valid_match(results: List[Dict[str, Any]], fallback_platform: str) -> Optional[Dict[str, Any]]:
    for item in results or []:
        normalized = normalize_scraper_item(item, fallback_platform=fallback_platform)
        if normalized and normalized.get("current_price") is not None:
            return normalized
    return None


@router.post("/sync-price/{barcode}", response_model=SyncResponse)
def sync_price(
    barcode: str,
    platform: str = "Hasaki",
    db: Session = Depends(get_db),
    apify_service: ApifyClientService = Depends(get_apify_service),
):
    sku = db.query(SkuMaster).filter(SkuMaster.barcode == barcode).first()
    if not sku:
        raise HTTPException(status_code=404, detail="Product not found in SkuMaster")

    existing_link = (
        db.query(CompetitorLink)
        .filter(CompetitorLink.barcode == barcode, CompetitorLink.platform == platform)
        .first()
    )

    if existing_link:
        target_url = existing_link.url
        actor_id = settings.HASAKI_SCRAPER_ACTOR_ID
    else:
        url_encoded_name = urllib.parse.quote_plus(sku.product_name)
        target_url = f"https://hasaki.vn/tim-kiem?q={url_encoded_name}"
        actor_id = settings.HASAKI_SEARCH_ACTOR_ID

    try:
        results = apify_service.run_scraper(actor_id=actor_id, target_url=target_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

    if not results:
        return {"status": "not_found", "message": "No results found from scraper"}

    top_results = results[:5] if isinstance(results, list) else []
    match = select_first_valid_match(top_results, fallback_platform=platform)

    if not match and isinstance(top_results, list):
        # Last-resort fallback for unusual payload shapes
        for item in top_results:
            if isinstance(item, dict):
                match = normalize_scraper_item(item, fallback_platform=platform)
                if match:
                    break

    if not match or match.get("current_price") is None:
        return {"status": "not_found", "message": "No valid match found."}

    price = match.get("current_price")
    scraped_price_int = parse_price_to_int(price)
    if scraped_price_int is None:
        return {"status": "error", "message": "Matched product does not contain a usable price."}

    if not existing_link and match.get("url"):
        new_link = CompetitorLink(
            barcode=barcode,
            platform=platform,
            url=match.get("url"),
            platform_item_id=match.get("sku_platform"),
        )
        db.add(new_link)
        db.commit()

    new_price = PriceHistory(
        barcode=barcode,
        platform=platform,
        scraped_price=scraped_price_int,
        promotion=match.get("promotion"),
        raw_data=match.get("raw_data"),
    )
    db.add(new_price)
    db.commit()

    return {
        "status": "success",
        "matched_product": match,
        "updated_price": scraped_price_int,
    }


logger = logging.getLogger(__name__)

async def execute_bulk_sync(db: Session):
    try:
        # We try to filter by is_active if it exists, otherwise just query all.
        # Assuming is_active is on SkuMaster based on requirements.
        active_skus = db.query(SkuMaster).filter(getattr(SkuMaster, "is_active", True) == True).all()
        
        apify_service = get_apify_service()

        for sku in active_skus:
            competitor_links = db.query(CompetitorLink).filter(CompetitorLink.barcode == sku.barcode).all()
            
            for link in competitor_links:
                try:
                    # Using existing get_apify_service() for tasks
                    actor_id = getattr(settings, "HASAKI_SCRAPER_ACTOR_ID", "default_actor_id")
                    # Since existing code is synchronous apify_service.run_scraper, we run it in thread or directly if it's fine.
                    apify_service.run_scraper(actor_id=actor_id, target_url=link.url)
                except Exception as e:
                    logger.error(f"Error syncing SKU {sku.barcode} with URL {link.url}: {e}")
                
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
    except Exception as e:
        logger.error(f"Fatal error during bulk sync: {e}")

@router.post("/v1/sync/all", status_code=status.HTTP_202_ACCEPTED)
async def trigger_bulk_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(execute_bulk_sync, db)
    return {"status": "processing", "message": "Bulk synchronization started successfully"}

