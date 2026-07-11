# backend/app/services/scrapers/strategies/pharmacity.py
"""
Pharmacity.com parser — transforms raw Apify output into CompetitorPriceDTO.

Apify raw shape example:
{
    "current_price": "501.500 ₫/Chai",
    "original_price": "530.000 ₫",
    "url": "https://www.pharmacity.vn/sua-rua-mat-cetaphil-diu-lanh-500ml.html",
    "hierarchy": "Chăm sóc da mặt > Sữa rửa mặt > Cetaphil",
    "promotion": "Mua 1 tặng 1 khẩu trang",
    "stock_status": "Còn hàng",
    ...
}

Notes:
  • JSON thô Pharmacity THIẾU trường "name" / "title" rõ ràng.
  • Tên sản phẩm phải bóc tách từ "hierarchy" (phần tử cuối) hoặc từ "url".
  • Giá dính đơn vị phân phối: "501.500 ₫/Chai" → regex cắt → 501500
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from app.services.scrapers.base import BaseScraper, CompetitorPriceDTO, clean_price_string

logger = logging.getLogger(__name__)

PLATFORM = "pharmacity"
DEFAULT_SHOP = "Pharmacity"


def _extract_name_from_url(url: str) -> Optional[str]:
    """
    Bóc tách tên sản phẩm tạm thời từ URL slug.
    'https://www.pharmacity.vn/sua-rua-mat-cetaphil-diu-lanh-500ml.html'
      → 'sua rua mat cetaphil diu lanh 500ml'
    """
    if not url:
        return None
    # Lấy phần path cuối
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    # Bỏ đuôi .html
    slug = re.sub(r"\.html?$", "", slug, flags=re.IGNORECASE)
    # Decode URL encoding
    slug = unquote(slug)
    # Thay dấu gạch ngang bằng khoảng trắng
    name = slug.replace("-", " ").strip()
    return name.title() if name else None


def _extract_name_from_hierarchy(hierarchy: Any) -> Optional[str]:
    """
    Lấy phần tử cuối cùng của hierarchy.
    Hierarchy có thể là:
      - str:  "Chăm sóc da mặt > Sữa rửa mặt > Cetaphil Gentle Skin Cleanser 500ml"
      - list: [{"name": "Chăm sóc da mặt"}, {"name": "Sữa rửa mặt"}, ...]
    """
    if isinstance(hierarchy, str) and hierarchy:
        parts = [p.strip() for p in hierarchy.split(">")]
        return parts[-1] if parts else None

    if isinstance(hierarchy, list) and hierarchy:
        last = hierarchy[-1]
        if isinstance(last, dict):
            return last.get("name") or last.get("title")
        return str(last)

    return None


class PharmacityScraper(BaseScraper):
    """Pharmacity strategy implementation."""

    # ---------- provider layer ----------
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
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
                logger.warning(f"[PharmacityParser] skipped item: {e}")
        return dtos

    # ---------- internal ----------
    @staticmethod
    def _parse_single(item: Dict[str, Any], barcode: str) -> CompetitorPriceDTO | None:
        # --- product_name ---
        # Priority: hierarchy last element > URL slug > generic fallback
        product_name = (
            item.get("title")
            or item.get("name")
            or _extract_name_from_hierarchy(item.get("hierarchy"))
            or _extract_name_from_url(item.get("url"))
        )
        if not product_name:
            return None

        # --- price: "501.500 ₫/Chai" → 501500 ---
        raw_price = item.get("current_price") if item.get("current_price") is not None else item.get("price")
        price = clean_price_string(raw_price)
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
        if not raw_payload:
            return {}
        return {
            "platform": "Pharmacity",
            "title": (
                raw_payload.get("title")
                or _extract_name_from_hierarchy(raw_payload.get("hierarchy"))
                or _extract_name_from_url(raw_payload.get("url"))
            ),
            "current_price": clean_price_string(raw_payload.get("current_price")),
            "original_price": clean_price_string(raw_payload.get("original_price")),
            "promotion": raw_payload.get("promotion"),
            "url": raw_payload.get("url"),
            "stock_status": raw_payload.get("stock_status"),
            "raw_data": raw_payload,
        }
