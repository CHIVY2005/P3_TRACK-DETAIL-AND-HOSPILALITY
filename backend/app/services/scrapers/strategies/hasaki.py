# backend/app/services/scrapers/strategies/hasaki.py
"""
Hasaki.vn parser — transforms raw Apify output into CompetitorPriceDTO.

Apify raw shape example:
{
    "title": "Sữa Rửa Mặt Cetaphil Dịu Lành 500ml",
    "current_price": "413.000 ₫",
    "original_price": "459.000 ₫",
    "url": "https://hasaki.vn/san-pham/...",
    "stock_status": "Còn hàng",
    "promotion": "Mua 2 giảm 5%",
    ...
}
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string

logger = logging.getLogger(__name__)

PLATFORM = "hasaki"
DEFAULT_SHOP = "Hasaki"


class HasakiScraper(BaseScraper):
    """Hasaki.vn strategy implementation."""

    # ---------- provider layer ----------
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        # Actual Apify call is handled by the orchestrator (sync.py)
        # This stub exists so unit-tests can call execute_pipeline directly
        return {}

    # ---------- parser layer ----------
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
                logger.warning(f"[HasakiParser] skipped item: {e}")
        return dtos

    # ---------- internal ----------
    @staticmethod
    def _parse_single(item: Dict[str, Any], barcode: str) -> CompetitorPriceDTO | None:
        # --- product_name: key "title" ---
        product_name = item.get("title") or item.get("name") or ""
        if not product_name:
            return None

        # --- price: "413.000 ₫" → 413000 ---
        price = clean_price_string(
            item.get("current_price") if item.get("current_price") is not None else item.get("price")
        )
        if price is None:
            return None

        # --- stock ---
        stock_raw = str(item.get("stock_status") or item.get("availability") or "").lower()
        is_in_stock = stock_raw not in ("hết hàng", "out of stock", "unavailable", "")

        # --- promotion ---
        promotion_info = item.get("promotion") or item.get("discount_info") or None
        if isinstance(promotion_info, list):
            promotion_info = "; ".join(str(p) for p in promotion_info)

        return CompetitorPriceDTO(
            barcode=barcode,
            platform=PLATFORM,
            product_name=str(product_name).strip(),
            shop_name=DEFAULT_SHOP,
            competitor_price=price,
            is_in_stock=is_in_stock,
            promotion_info=promotion_info,
            raw_payload=item,
        )

    # ---------- legacy compat ----------
    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy pipeline compatibility — normalise a single Hasaki item."""
        if not raw_payload:
            return {}
        return {
            "platform": "Hasaki",
            "title": raw_payload.get("title"),
            "current_price": clean_price_string(raw_payload.get("current_price")),
            "original_price": clean_price_string(raw_payload.get("original_price")),
            "promotion": raw_payload.get("promotion"),
            "url": raw_payload.get("url"),
            "stock_status": raw_payload.get("stock_status"),
            "raw_data": raw_payload,
        }
