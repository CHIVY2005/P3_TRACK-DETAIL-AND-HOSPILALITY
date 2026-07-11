# backend/app/routes/sync.py
"""
Sync endpoints — single-barcode sync + bulk async sync for 200+ SKU.

Architecture:
    POST /sync-price/{barcode}         → synchronous single-product scrape
    POST /v1/sync/all                  → HTTP 202 + BackgroundTasks bulk scrape
    POST /v1/sync/force                → HTTP 202 + force re-scrape all platforms

Bulk sync uses asyncio.gather to fan-out Apify calls concurrently.
The DTO pipeline is: raw_json → ScraperFactory.parse_to_dto → UPSERT price_history.
"""
import re
import urllib.parse
from typing import Any, Dict, List, Optional

import asyncio
import random
import logging

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings, get_actor_id_for_platform
from app.db.models import CompetitorLink, PriceHistory, SkuMaster
from app.db.session import get_db, SessionLocal
from app.services.apify_client import ApifyClientService, get_apify_service
from app.services.scrapers.base import CompetitorPriceDTO, clean_price_string
from app.services.scrapers.factory import ScraperFactory, SUPPORTED_PLATFORMS

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class SyncResponse(BaseModel):
    status: str
    matched_product: Optional[Dict[str, Any]] = None
    updated_price: Optional[float] = None
    message: Optional[str] = None


class BulkSyncResponse(BaseModel):
    status: str
    message: str


# ---------------------------------------------------------------------------
# Utility: legacy price parser (kept for single-barcode route)
# ---------------------------------------------------------------------------
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
    barcode = raw_item.get("barcode") or raw_item.get("sku") or raw_item.get("item_id")
    brand_name = raw_item.get("brand_name") or raw_item.get("brand") or raw_item.get("manufacturer")
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
    promotion = raw_item.get("promotion") or raw_item.get("promotion_info") or (
        f"Giảm {discount_pct}%" if discount_pct not in (None, "", 0) else None
    )

    sku_platform = raw_item.get("sku_platform") or raw_item.get("item_id") or raw_item.get("id") or raw_item.get("sku")
    shop_name = raw_item.get("shop_name") or raw_item.get("sellerName") or raw_item.get("merchant_name") or fallback_platform

    normalized = {
        "platform": raw_item.get("platform") or fallback_platform,
        "barcode": str(barcode) if barcode is not None else None,
        "brand_name": brand_name,
        "shop_name": shop_name,
        "title": title,
        "current_price": current_price,
        "competitor_price": current_price,
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


# ---------------------------------------------------------------------------
# Endpoint 1: Single barcode sync (legacy — synchronous)
# ---------------------------------------------------------------------------
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
        product_name=match.get("title"),
        shop_name=match.get("shop_name", match.get("platform", platform)),
        scraped_price=scraped_price_int,
        is_in_stock=True,
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


# ---------------------------------------------------------------------------
# DTO → PostgreSQL UPSERT pipeline
# ---------------------------------------------------------------------------
def upsert_dtos_to_db(dtos: List[CompetitorPriceDTO], db: Session) -> int:
    """
    Write a batch of clean CompetitorPriceDTOs into `price_history`.
    Returns the number of records written.
    """
    count = 0
    for dto in dtos:
        record = PriceHistory(
            barcode=dto.barcode,
            platform=dto.platform,
            product_name=dto.product_name,
            shop_name=dto.shop_name,
            scraped_price=dto.competitor_price,
            is_in_stock=dto.is_in_stock,
            promotion=dto.promotion_info,
            raw_data=dto.raw_payload,
        )
        db.add(record)
        count += 1

    if count > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB commit failed: {e}")
            raise
    return count


# ---------------------------------------------------------------------------
# Async worker: scrape a single SKU across all linked platforms
# ---------------------------------------------------------------------------
async def _scrape_single_sku(
    sku: SkuMaster,
    db: Session,
    apify_service: ApifyClientService,
) -> int:
    """
    Scrape one SKU across all its competitor_links.
    Returns number of DTO records persisted.
    """
    links = db.query(CompetitorLink).filter(CompetitorLink.barcode == sku.barcode).all()

    total = 0
    for link in links:
        platform = link.platform.lower().strip()
        try:
            actor_id = get_actor_id_for_platform(platform)
        except ValueError:
            logger.warning(f"No actor for platform '{platform}', skipping.")
            continue

        try:
            raw_items = apify_service.run_scraper(actor_id=actor_id, target_url=link.url)
            if not raw_items:
                continue
            if not isinstance(raw_items, list):
                raw_items = [raw_items]

            scraper = ScraperFactory.get_scraper(platform)
            dtos = scraper.parse_to_dto(raw_items, barcode=sku.barcode)
            if dtos:
                total += upsert_dtos_to_db(dtos, db)

        except Exception as e:
            logger.error(f"Error scraping {sku.barcode}@{platform}: {e}")

    return total


# ---------------------------------------------------------------------------
# Bulk sync background worker
# ---------------------------------------------------------------------------
async def execute_bulk_sync(db: Session):
    """
    Fan-out scrape for ALL active SKUs across ALL their competitor links.
    Called as a BackgroundTask — runs after HTTP 202 is returned.
    """
    try:
        all_skus = db.query(SkuMaster).all()
        apify_service = get_apify_service()
        total_records = 0

        logger.info(f"[BulkSync] Starting for {len(all_skus)} SKUs…")

        # Process in batches of 10 to avoid overwhelming Apify
        batch_size = 10
        for i in range(0, len(all_skus), batch_size):
            batch = all_skus[i:i + batch_size]

            tasks = [
                _scrape_single_sku(sku, db, apify_service)
                for sku in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in results:
                if isinstance(r, int):
                    total_records += r
                elif isinstance(r, Exception):
                    logger.error(f"[BulkSync] batch error: {r}")

            # Polite delay between batches
            await asyncio.sleep(random.uniform(1.0, 3.0))

        logger.info(f"[BulkSync] Completed. Total records written: {total_records}")

    except Exception as e:
        logger.error(f"[BulkSync] Fatal error: {e}")


# ---------------------------------------------------------------------------
# Endpoint 2: Bulk sync — HTTP 202 + BackgroundTasks
# ---------------------------------------------------------------------------
@router.post("/v1/sync/all", status_code=status.HTTP_202_ACCEPTED, response_model=BulkSyncResponse)
async def trigger_bulk_sync(background_tasks: BackgroundTasks):
    db = SessionLocal()
    background_tasks.add_task(execute_bulk_sync, db)
    return {
        "status": "processing",
        "message": "Sync process initiated in background",
    }


# ---------------------------------------------------------------------------
# Endpoint 3: Force sync — re-scrape everything immediately
# ---------------------------------------------------------------------------
@router.post("/v1/sync/force", status_code=status.HTTP_202_ACCEPTED, response_model=BulkSyncResponse)
async def trigger_force_sync(background_tasks: BackgroundTasks):
    db = SessionLocal()
    background_tasks.add_task(execute_bulk_sync, db)
    return {
        "status": "processing",
        "message": "Force sync initiated in background — all platforms will be re-scraped",
    }
