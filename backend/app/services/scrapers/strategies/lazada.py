# backend/app/services/scrapers/strategies/lazada.py
"""
Lazada.vn parser — transforms raw Apify Lazada-scraper output into CompetitorPriceDTO.

Lazada Apify actor shape:
{
    "name": "Sữa Rửa Mặt Cetaphil…",
    "price": 385000,              ← plain VND
    "originalPrice": 459000,
    "sellerName": "Cetaphil Official",
    "inStock": true,
    "discount": "-16%",
    "itemId": "i987654321",
    "url": "https://www.lazada.vn/products/...",
    ...
}
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string

logger = logging.getLogger(__name__)

PLATFORM = "lazada"


class LazadaScraper(BaseScraper):
    """Lazada strategy implementation."""

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
                logger.warning(f"[LazadaParser] skipped item: {e}")
        return dtos

    @staticmethod
    def _parse_single(item: Dict[str, Any], barcode: str) -> CompetitorPriceDTO | None:
        product_name = item.get("name") or item.get("title") or item.get("product_name") or ""
        if not product_name:
            return None

        raw_price = item.get("price") if item.get("price") is not None else item.get("current_price")
        price = clean_price_string(raw_price)
        if price is None or price <= 0:
            return None

        shop_name = item.get("sellerName") or item.get("shop_name") or "Lazada Seller"

        in_stock = item.get("inStock", True)
        if isinstance(in_stock, str):
            in_stock = in_stock.lower() not in ("false", "0", "out_of_stock")
        is_in_stock = bool(in_stock)

        discount = item.get("discount") or item.get("discount_pct")
        promotion_info = str(discount) if discount else None

        raw_payload = dict(item)
        raw_payload["url"] = raw_payload.get("url") or LazadaScraper._build_product_url(item)

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
        raw_url = str(item.get("url") or "").strip()
        if raw_url:
            return raw_url

        item_id = str(item.get("itemId") or item.get("item_id") or "").strip()
        sku_id = str(item.get("skuId") or item.get("sku_id") or item.get("sellerSku") or "").strip()

        item_match = re.search(r"i(\d+)", item_id)
        sku_match = re.search(r"s(\d+)", sku_id)
        normalized_item_id = item_match.group(1) if item_match else item_id if item_id.isdigit() else ""
        normalized_sku_id = sku_match.group(1) if sku_match else sku_id if sku_id.isdigit() else ""

        if normalized_item_id and normalized_sku_id:
            return f"https://www.lazada.vn/products/pdp-i{normalized_item_id}-s{normalized_sku_id}.html"
        if normalized_item_id:
            return f"https://www.lazada.vn/products/i{normalized_item_id}.html"
        return None

    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return raw_payload
