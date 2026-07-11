# backend/app/services/scrapers/base.py
"""
Core contracts for the omnichannel scraping pipeline.

Architecture:
    BaseScraper.fetch_raw_json  →  provider layer  (Apify / BrightData / ZenRows)
    BaseScraper.parse_to_dto    →  platform parser  (Hasaki / Pharmacity / Shopee …)

Swapping the data-provider only requires overriding `fetch_raw_json`;
`parse_to_dto` stays untouched because it's pure business-logic parsing.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contract DTO — the *single source of truth* that every platform must emit
# ---------------------------------------------------------------------------
class CompetitorPriceDTO(BaseModel):
    """
    Clean, validated data object written into `price_history`.
    Every platform scraper MUST emit this shape.
    """
    barcode: str = Field(..., description="Mã vạch khớp nối database")
    platform: str = Field(..., description="Tên sàn bằng chữ thường (shopee, hasaki, …)")
    product_name: str = Field(..., description="Tên sản phẩm bóc từ sàn đối thủ")
    shop_name: str = Field(..., description="Tên shop bán; mặc định = tên sàn với Hasaki/Pharmacity")
    competitor_price: int = Field(..., description="Giá bán sạch (VND), số nguyên")
    is_in_stock: bool = Field(True, description="Trạng thái còn hàng")
    promotion_info: Optional[str] = Field(None, description="Thông tin giảm giá / quà tặng")
    raw_payload: dict = Field(default_factory=dict, description="JSON thô từ Apify → JSONB Postgres")

    class Config:
        # Allow arbitrary types so raw_payload can hold anything
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Utility: price string → int
# ---------------------------------------------------------------------------
def clean_price_string(raw_value: Any) -> Optional[int]:
    """
    Normalise any price representation to a plain integer in VND.

    Examples handled:
        "413.000 ₫"          → 413000
        "501.500 ₫/Chai"     → 501500
        "1.250.000đ"         → 1250000
        495000                → 495000
        49500000 (Shopee x100k) → handled by caller
        "Liên hệ"            → None
    """
    if raw_value is None:
        return None

    if isinstance(raw_value, (int, float)):
        v = int(raw_value)
        return v if v > 0 else None

    if isinstance(raw_value, str):
        # Strip everything except digits and dots
        # "501.500 ₫/Chai" → "501.500"
        stripped = re.sub(r"[^\d.]", "", raw_value.strip())
        if not stripped:
            return None

        # Vietnamese price format uses dots as thousand-separators:
        # "501.500" → 501500,  "1.250.000" → 1250000
        # But we must distinguish from decimal dots (e.g. "4.9" rating).
        # Rule: if any segment after a dot has exactly 3 digits → thousand sep.
        parts = stripped.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            # Thousand-separated: join all parts
            return int("".join(parts))

        # Otherwise treat entire string as a number (remove dots)
        digits_only = stripped.replace(".", "")
        if digits_only.isdigit():
            return int(digits_only)

    return None


# ---------------------------------------------------------------------------
# Abstract Base Scraper
# ---------------------------------------------------------------------------
class BaseScraper(ABC):
    """
    Strategy interface.  Each platform has its own subclass implementing:
      • fetch_raw_json   — call Apify / BrightData / ZenRows
      • parse_to_dto     — transform raw JSON → list[CompetitorPriceDTO]

    The `clean_data` legacy method is preserved for backward compatibility.
    """

    # ------ provider layer (override for BrightData / ZenRows) ------
    @abstractmethod
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        """Call the external provider and return the raw JSON list/dict."""
        ...

    # ------ parser layer (pure business logic — never changes on provider swap) ------
    @abstractmethod
    def parse_to_dto(
        self,
        raw_items: List[Dict[str, Any]],
        barcode: str,
    ) -> List[CompetitorPriceDTO]:
        """
        Convert raw Apify/BrightData items into clean DTOs.
        `barcode` is injected by the orchestrator so the parser can tag each DTO.
        """
        ...

    # ------ legacy compat ------
    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method kept for backward compatibility with old pipeline."""
        return raw_payload

    # ------ fixture fallback ------
    def get_fixture_fallback(self) -> Dict[str, Any]:
        """Centralized Fixture Fallback mechanism."""
        return {
            "platform": "Fallback",
            "title": "Mock Product (Fallback)",
            "current_price": 999999,
            "original_price": 999999,
            "promotion": None,
            "sku_platform": "000000",
            "hierarchy": "Fallback > Category",
            "url": "https://fallback.local",
            "stock_status": "Out of Stock",
            "rating": 0.0,
            "raw_data": {"fallback": True},
        }

    # ------ full pipeline ------
    async def execute_pipeline(self, target_url: str) -> Dict[str, Any]:
        try:
            raw_data = await self.fetch_raw_json(target_url)
            return self.clean_data(raw_data)
        except Exception as e:
            logger.error(f"Scraping failed for {target_url}: {e}")
            return self.get_fixture_fallback()
