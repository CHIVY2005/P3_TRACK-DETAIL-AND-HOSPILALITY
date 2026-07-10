from typing import Any, Dict, Optional


def map_marketplace_result(platform: str, payload: Dict[str, Any], fallback_url: Optional[str] = None) -> Dict[str, Any]:
    price = _to_float(payload.get("net_price") or payload.get("price") or payload.get("current_price") or payload.get("scraped_price"))
    original_price = _to_float(payload.get("raw_price") or payload.get("price_before_discount") or payload.get("original_price") or price)
    discount = max((original_price or 0.0) - (price or 0.0), 0.0) if price is not None else 0.0

    return {
        "platform": platform,
        "title": payload.get("title") or payload.get("name"),
        "raw_price": original_price or price,
        "net_price": price,
        "discount": discount,
        "voucher_details": payload.get("voucher_info") or payload.get("voucher_details"),
        "promo_mechanics": payload.get("promotion_name") or payload.get("promotion"),
        "url": payload.get("url") or fallback_url,
        "stock_status": payload.get("availability") or payload.get("stock_status") or "IN_STOCK",
        "rating": _to_float(payload.get("rating_star") or payload.get("rating")),
    }


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch in {".", ","})
        return float(cleaned.replace(",", ""))
    except ValueError:
        return None
