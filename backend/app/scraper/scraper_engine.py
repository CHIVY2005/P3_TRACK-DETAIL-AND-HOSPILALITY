import asyncio
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import get_actor_id_for_platform
from app.db import models
from app.services.apify_client import ApifyClientService
from app.services.cpi_calculator import calculate_cpi_for_product, check_price_anomaly
from app.services.link_discovery import ensure_competitor_link
from app.services.scrapers import CompetitorPriceDTO, ScraperFactory


COMPETITORS = ["Shopee", "Lazada", "TikTok Shop", "GrabMart", "Pharmacity", "Hasaki"]
_PLATFORM_KEY_MAP = {
    "Shopee": "shopee",
    "Lazada": "lazada",
    "TikTok Shop": "tiktok_shop",
    "GrabMart": "grabmart",
    "Pharmacity": "pharmacity",
    "Hasaki": "hasaki",
}


def _platform_key(platform_name: str) -> str:
    return _PLATFORM_KEY_MAP.get(platform_name, platform_name.lower().replace(" ", "_"))


def _to_price_record(
    competitor_name: str,
    dto: CompetitorPriceDTO,
    fallback_url: Optional[str] = None,
) -> Dict[str, Any]:
    raw_payload = dict(dto.raw_payload or {})
    url = raw_payload.get("url") or fallback_url
    return {
        "raw_price": float(dto.competitor_price),
        "discount": 0.0,
        "net_price": float(dto.competitor_price),
        "stock_status": "IN_STOCK" if dto.is_in_stock else "OUT_OF_STOCK",
        "is_suspicious": False,
        "voucher_details": dto.promotion_info,
        "promo_mechanics": dto.promotion_info,
        "url": url,
        "raw_payload": raw_payload,
        "competitor_name": competitor_name,
    }


def _fallback_price(product_guardian_price: float, competitor_name: str, barcode: str, fallback_url: str | None = None) -> dict:
    daily_seed = f"{datetime.utcnow().date().isoformat()}:{barcode}:{competitor_name}"
    rng = random.Random(daily_seed)

    if competitor_name == "Shopee":
        price_factor = rng.uniform(0.82, 0.98)
        discount_pct = rng.choice([0.0, 0.05, 0.10, 0.15])
        voucher = rng.choice([None, "Mã giảm 10k", "Mã giảm 20k", "Freeship Extra"])
        promo = rng.choice([None, "Mua kèm deal sốc", "Flash Sale"])
    elif competitor_name == "Lazada":
        price_factor = rng.uniform(0.85, 0.97)
        discount_pct = rng.choice([0.0, 0.05, 0.08, 0.12])
        voucher = rng.choice([None, "Voucher tích lũy", "Mã giảm 15k"])
        promo = rng.choice([None, "Combo mua 2 giảm 5%", "Flash Sale"])
    elif competitor_name == "TikTok Shop":
        price_factor = rng.uniform(0.78, 0.95)
        discount_pct = rng.choice([0.0, 0.10, 0.20])
        voucher = rng.choice([None, "Voucher Livestream 25k", "Mã người mới"])
        promo = rng.choice([None, "Flash Sale hàng hiệu"])
    elif competitor_name == "GrabMart":
        price_factor = rng.uniform(0.98, 1.15)
        discount_pct = 0.0
        voucher = None
        promo = None
    else:
        price_factor = rng.uniform(0.95, 1.05)
        discount_pct = rng.choice([0.0, 0.05])
        voucher = None
        promo = None

    raw_price = round(product_guardian_price * price_factor, -3)
    discount_amount = round(raw_price * discount_pct, -3)
    net_price = raw_price - discount_amount

    voucher_val = 0
    if voucher:
        if "10k" in voucher:
            voucher_val = 10000
        elif "15k" in voucher:
            voucher_val = 15000
        elif "20k" in voucher:
            voucher_val = 20000
        elif "25k" in voucher:
            voucher_val = 25000
        net_price = max(1000, net_price - voucher_val)

    comp_slug = competitor_name.lower().replace(" ", "")
    url = fallback_url or f"https://www.{comp_slug}.vn/search?q={barcode}"

    return {
        "raw_price": raw_price,
        "net_price": net_price,
        "discount": discount_amount,
        "stock_status": "IN_STOCK",
        "voucher_details": voucher,
        "promo_mechanics": promo,
        "url": url,
        "raw_payload": {
            "fallback": True,
            "competitor_name": competitor_name,
            "barcode": barcode,
        },
    }


def _fetch_raw_items(competitor_name: str, target_url: str) -> List[Dict[str, Any]]:
    actor_id = get_actor_id_for_platform(_platform_key(competitor_name))
    raw_items = ApifyClientService().run_scraper(actor_id=actor_id, target_url=target_url)
    if raw_items is None:
        return []
    if isinstance(raw_items, list):
        return [item for item in raw_items if isinstance(item, dict)]
    if isinstance(raw_items, dict):
        return [raw_items]
    return []


async def _scrape_platform(
    db: Session,
    product: models.Product,
    competitor_name: str,
) -> Optional[dict]:
    link = ensure_competitor_link(db, product, competitor_name)
    target_url = link.url if link else ""
    raw_items = _fetch_raw_items(competitor_name, target_url)

    price_data: Optional[dict] = None
    if raw_items:
        scraper = ScraperFactory.get_scraper(_platform_key(competitor_name))
        dtos = scraper.parse_to_dto(raw_items, barcode=product.barcode)
        if dtos:
            price_data = _to_price_record(
                competitor_name=competitor_name,
                dto=dtos[0],
                fallback_url=link.url if link else None,
            )

    if not price_data:
        price_data = _fallback_price(product.guardian_price, competitor_name, product.barcode, link.url if link else None)

    if link and price_data.get("url") and link.url != price_data["url"]:
        link.url = price_data["url"]
        link.discovery_method = "scraped"

    price_data["is_suspicious"] = check_price_anomaly(db, product.id, competitor_name, price_data["net_price"])
    return price_data


async def scrape_competitor_prices_for_product_async(db: Session, product_id: int) -> list:
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return []

    new_prices = []

    for competitor in COMPETITORS:
        price_data = await _scrape_platform(db, product, competitor)
        if not price_data:
            continue

        price_record = models.CompetitorPrice(
            product_id=product.id,
            competitor_name=competitor,
            raw_price=price_data["raw_price"],
            discount=price_data["discount"],
            net_price=price_data["net_price"],
            stock_status=price_data.get("stock_status", "IN_STOCK"),
            is_suspicious=price_data.get("is_suspicious", False),
            voucher_details=price_data.get("voucher_details"),
            promo_mechanics=price_data.get("promo_mechanics"),
            url=price_data.get("url"),
            raw_payload=price_data.get("raw_payload"),
            scraped_at=datetime.utcnow(),
        )
        db.add(price_record)
        new_prices.append(price_record)

    db.commit()
    calculate_cpi_for_product(db, product.id)
    return new_prices


def scrape_realtime_competitor_prices(db: Session, product_id: int) -> list:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id))
    return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id))


def run_scraper_for_all_products(db: Session):
    products = db.query(models.Product).all()
    results = {}
    for product in products:
        results[product.id] = scrape_realtime_competitor_prices(db, product.id)
    return results
