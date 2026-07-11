# backend/app/services/scrapers/strategies/shopee.py
"""
Shopee.vn parser — transforms raw Apify Shopee-scraper output into CompetitorPriceDTO.

Apify raw shape (xtracto/shopee-scraper):
{
    "item_id": 12345678,
    "shop_id": 87654321,
    "title": "Sữa Rửa Mặt Cetaphil…",
    "price": 38500000,           ← Shopee hệ float ×100,000  (385000₫ = 38500000)
    "price_before_discount": 42000000,
    "shop_name": "CETAPHIL Official Store",
    "shop_is_official_shop": true,
    "availability": "IN_STOCK",
    "discount_pct": 8,
    "rating_star": 4.9,
    "breadcrumb": [{"name":"Skincare","url":"..."}],
    ...
}

The Shopee Apify actor stores prices as `price / 100_000` to get VND.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string

logger = logging.getLogger(__name__)

PLATFORM = "shopee"
SHOPEE_PRICE_DIVISOR = 100_000  # Shopee API stores price × 100,000


class ShopeeScraper(BaseScraper):
    """Shopee strategy implementation."""

    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        return {}

    def parse_to_dto(
        self,
        raw_items: List[Dict[str, Any]],
        barcode: str,
    ) -> List[CompetitorPriceDTO]:
        dtos: List[CompetitorPriceDTO] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            try:
                dto = self._parse_single(item, barcode)
                if dto is not None:
                    dtos.append(dto)
            except Exception as e:
                logger.warning(f"[ShopeeParser] skipped item: {e}")
        return dtos

    @staticmethod
    def _parse_single(item: Dict[str, Any], barcode: str) -> CompetitorPriceDTO | None:
        product_name = item.get("title") or item.get("name") or ""
        if not product_name:
            return None

        # --- price: Shopee hệ ×100,000 ---
        raw_price = item.get("price") if item.get("price") is not None else item.get("current_price")
        if raw_price is None:
            return None

        if isinstance(raw_price, (int, float)) and raw_price > 1_000_000:
            # Likely Shopee internal format — divide
            price = int(raw_price / SHOPEE_PRICE_DIVISOR)
        else:
            price = clean_price_string(raw_price)

        if price is None or price <= 0:
            return None

        # --- shop ---
        shop_name = item.get("shop_name") or item.get("seller_name") or "Shopee Seller"

        # --- stock ---
        avail = str(item.get("availability") or item.get("stock_status") or "").upper()
        is_in_stock = avail not in ("OUT_OF_STOCK", "UNAVAILABLE", "")

        # --- promotion ---
        discount = item.get("discount_pct") or item.get("discount")
        promotion_info = f"Giảm {discount}%" if discount else None

        raw_payload = dict(item)
        raw_payload["url"] = raw_payload.get("url") or ShopeeScraper._build_product_url(item)

        return CompetitorPriceDTO(
            barcode=barcode,
            platform=PLATFORM,
            product_name=str(product_name).strip(),
            shop_name=str(shop_name).strip(),
            competitor_price=price,
            is_in_stock=is_in_stock,
            promotion_info=promotion_info,
            raw_payload=raw_payload,
        )

    @staticmethod
    def _build_product_url(item: Dict[str, Any]) -> str | None:
        breadcrumbs = item.get("breadcrumb") or []
        if isinstance(breadcrumbs, list):
            for crumb in reversed(breadcrumbs):
                if isinstance(crumb, dict):
                    url = str(crumb.get("url") or "").strip()
                    if "shopee.vn" in url and re.search(r"-i\.\d+\.\d+", url):
                        return url

        shop_id = item.get("shop_id") or item.get("shopid")
        item_id = item.get("item_id") or item.get("itemid")
        if shop_id and item_id:
            return f"https://shopee.vn/product/{shop_id}/{item_id}"
        return None

    # ---------- legacy compat ----------
    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_payload or not isinstance(raw_payload, list) or len(raw_payload) == 0:
            return {}

        item = raw_payload[0]

        current_price = item.get("price")
        original_price = item.get("price_before_discount")
        discount_pct = item.get("discount_pct")
        promotion = f"Giảm {discount_pct}%" if discount_pct else None

        breadcrumbs = item.get("breadcrumb", [])
        hierarchy = " > ".join([b.get("name") for b in breadcrumbs]) if breadcrumbs else None

        if breadcrumbs:
            url = breadcrumbs[-1].get("url")
        else:
            url = f"https://shopee.vn/product/{item.get('shop_id')}/{item.get('item_id')}"

        return {
            "platform": "Shopee",
            "title": item.get("title"),
            "current_price": current_price,
            "original_price": original_price,
            "promotion": promotion,
            "sku_platform": str(item.get("item_id")),
            "hierarchy": hierarchy,
            "url": url,
            "stock_status": item.get("availability"),
            "rating": item.get("rating_star"),
            "raw_data": raw_payload,
        }
