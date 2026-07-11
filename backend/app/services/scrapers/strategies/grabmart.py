# backend/app/services/scrapers/strategies/grabmart.py
"""
GrabMart parser — transforms raw Apify GrabMart output into CompetitorPriceDTO.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string

logger = logging.getLogger(__name__)

PLATFORM = "grabmart"
DEFAULT_SHOP = "GrabMart"


class GrabMartScraper(BaseScraper):
    """GrabMart strategy implementation."""

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
                logger.warning(f"[GrabMartParser] skipped item: {e}")
        return dtos

    @staticmethod
    def _parse_single(item: Dict[str, Any], barcode: str) -> CompetitorPriceDTO | None:
        product_name = item.get("title") or item.get("name") or ""
        if not product_name:
            return None

        raw_price = item.get("price") if item.get("price") is not None else item.get("current_price")
        price = clean_price_string(raw_price)
        if price is None or price <= 0:
            return None

        shop_name = item.get("merchant_name") or item.get("shop_name") or DEFAULT_SHOP

        stock_raw = str(item.get("stock_status") or item.get("availability") or "").upper()
        is_in_stock = stock_raw not in ("OUT_OF_STOCK", "UNAVAILABLE", "")

        promotion_info = item.get("promotion") or item.get("discount_info") or None

        return CompetitorPriceDTO(
            barcode=barcode,
            platform=PLATFORM,
            product_name=str(product_name).strip(),
            shop_name=str(shop_name).strip(),
            competitor_price=price,
            is_in_stock=is_in_stock,
            promotion_info=promotion_info,
            raw_payload=item,
        )

    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return raw_payload
