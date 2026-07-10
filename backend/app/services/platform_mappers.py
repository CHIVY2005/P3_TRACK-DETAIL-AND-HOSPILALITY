import re
from typing import Any, Dict, Optional


def map_marketplace_result(platform: str, payload: Dict[str, Any], fallback_url: Optional[str] = None) -> Dict[str, Any]:
    explicit_effective_price = _to_float(payload.get("effective_price") or payload.get("net_price"))
    sale_price = _to_float(payload.get("price") or payload.get("current_price") or payload.get("scraped_price"))
    bundle_price = _to_float(payload.get("bundle_price"))
    bundle_quantity = _to_float(payload.get("bundle_quantity") or payload.get("quantity"))
    if bundle_price is not None and bundle_quantity and bundle_quantity > 0:
        sale_price = bundle_price / bundle_quantity

    voucher_details = payload.get("voucher_info") or payload.get("voucher_details")
    voucher_amount = _to_float(
        payload.get("voucher_discount")
        or payload.get("voucher_amount")
        or payload.get("voucher_value")
    )
    if voucher_amount is None:
        voucher_amount = _voucher_amount_from_text(voucher_details)

    effective_price = explicit_effective_price
    if effective_price is None and sale_price is not None:
        effective_price = max(sale_price - voucher_amount, 0.0)

    original_price = _to_float(
        payload.get("raw_price")
        or payload.get("price_before_discount")
        or payload.get("original_price")
        or sale_price
        or effective_price
    )
    discount = max((original_price or 0.0) - (sale_price or effective_price or 0.0), 0.0)

    return {
        "platform": platform,
        "title": payload.get("title") or payload.get("name"),
        "raw_price": original_price or effective_price,
        "net_price": effective_price,
        "discount": discount,
        "voucher_details": voucher_details,
        "promo_mechanics": payload.get("promotion_name") or payload.get("promotion"),
        "url": payload.get("url") or fallback_url,
        "stock_status": _normalize_stock_status(payload.get("availability") or payload.get("stock_status")),
        "rating": _to_float(payload.get("rating_star") or payload.get("rating")),
    }


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch in {".", ","})
    if not cleaned:
        return None

    separators = [index for index, char in enumerate(cleaned) if char in {".", ","}]
    if separators:
        last_separator = separators[-1]
        decimal_digits = len(cleaned) - last_separator - 1
        if decimal_digits in {1, 2}:
            integer_part = "".join(ch for ch in cleaned[:last_separator] if ch.isdigit())
            decimal_part = "".join(ch for ch in cleaned[last_separator + 1 :] if ch.isdigit())
            cleaned = f"{integer_part}.{decimal_part}"
        else:
            cleaned = "".join(ch for ch in cleaned if ch.isdigit())
    try:
        return float(cleaned)
    except ValueError:
        return None


def _voucher_amount_from_text(value: Any) -> float:
    text = str(value or "").lower()
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*k\b", text)
    if match:
        return float(match.group(1).replace(",", ".")) * 1000.0
    return 0.0


def _normalize_stock_status(value: Any) -> str:
    normalized = str(value or "IN_STOCK").replace("_", "").replace(" ", "").lower()
    if normalized in {"false", "0", "outofstock", "oos", "unavailable", "soldout"}:
        return "OUT_OF_STOCK"
    return "IN_STOCK"
