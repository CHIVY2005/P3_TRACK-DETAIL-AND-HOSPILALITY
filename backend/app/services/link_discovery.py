import re
import unicodedata
from typing import Callable, Optional
from urllib.parse import parse_qs, quote, unquote, urlparse

from sqlalchemy.orm import Session

from app.db import models


PlatformNormalizer = Callable[[str], Optional[str]]


SEARCH_URL_BUILDERS = {
    "Shopee": lambda query: f"https://shopee.vn/search?keyword={quote(query)}",
    "Lazada": lambda query: f"https://www.lazada.vn/catalog/?q={quote(query)}",
    "Pharmacity": lambda query: (
        "https://www.pharmacity.vn/search"
        f"?keyword={quote(query)}&order=desc&order_by=de-xuat"
    ),
    "Hasaki": lambda query: f"https://hasaki.vn/tim-kiem.html?keyword={quote(query)}",
}

EXPECTED_HOSTS = {
    "Shopee": ("shopee.vn",),
    "Lazada": ("lazada.vn",),
    "Hasaki": ("hasaki.vn",),
    "Pharmacity": ("pharmacity.vn",),
}


def ensure_competitor_link(db: Session, product: models.Product, platform: str) -> Optional[models.CompetitorLink]:
    existing = (
        db.query(models.CompetitorLink)
        .filter(models.CompetitorLink.product_id == product.id, models.CompetitorLink.platform == platform)
        .first()
    )
    if existing:
        normalized = normalize_platform_url(platform, existing.url)
        if normalized is None:
            normalized = build_search_url(product, platform)

        if normalized and normalized != existing.url:
            existing.url = normalized
            existing.discovery_method = _mark_normalized(existing.discovery_method)
            db.commit()
            db.refresh(existing)
        return existing

    url = build_search_url(product, platform)
    if not url:
        return None

    link = models.CompetitorLink(
        product_id=product.id,
        platform=platform,
        url=url,
        discovery_method="search-driven",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def build_search_url(product: models.Product, platform: str) -> Optional[str]:
    builder = SEARCH_URL_BUILDERS.get(platform)
    if builder is None:
        return None

    query = _build_search_query(product)
    return builder(query)


def normalize_platform_url(platform: str, raw_url: str | None) -> Optional[str]:
    if not raw_url:
        return None

    cleaned = raw_url.strip()
    if not cleaned:
        return None

    normalizer = _NORMALIZERS.get(platform)
    if normalizer is None:
        return cleaned
    return normalizer(cleaned)


def _normalize_shopee_url(raw_url: str) -> Optional[str]:
    parsed = urlparse(raw_url)
    if not _host_matches(parsed.netloc, EXPECTED_HOSTS["Shopee"]):
        return None

    if "/search" in parsed.path and not parsed.query:
        return None

    shop_and_item = re.search(r"-i\.(\d+)\.(\d+)", parsed.path)
    if shop_and_item:
        shop_id, item_id = shop_and_item.groups()
        return f"https://shopee.vn/product/{shop_id}/{item_id}"

    detail_path = re.search(r"/product/(\d+)/(\d+)", parsed.path)
    if detail_path:
        shop_id, item_id = detail_path.groups()
        return f"https://shopee.vn/product/{shop_id}/{item_id}"

    query_params = parse_qs(parsed.query)
    keyword = query_params.get("keyword", [None])[0] or query_params.get("q", [None])[0]
    if keyword:
        return f"https://shopee.vn/search?keyword={quote(unquote(keyword))}"

    return "https://shopee.vn" + parsed.path if parsed.path else None


def _normalize_lazada_url(raw_url: str) -> Optional[str]:
    parsed = urlparse(raw_url)
    if not _host_matches(parsed.netloc, EXPECTED_HOSTS["Lazada"]):
        return None

    if "/catalog/" in parsed.path and not parsed.query:
        return None

    match = re.search(r"/products/(?:pdp-)?i(\d+)-s(\d+)\.html", parsed.path)
    if match:
        item_id, sku_id = match.groups()
        return f"https://www.lazada.vn/products/pdp-i{item_id}-s{sku_id}.html"

    query_params = parse_qs(parsed.query)
    keyword = query_params.get("q", [None])[0]
    if keyword:
        return f"https://www.lazada.vn/catalog/?q={quote(unquote(keyword))}"

    return "https://www.lazada.vn" + parsed.path if parsed.path else None


def _normalize_hasaki_url(raw_url: str) -> Optional[str]:
    parsed = urlparse(raw_url)
    if not _host_matches(parsed.netloc, EXPECTED_HOSTS["Hasaki"]):
        return None

    if "tim-kiem" in parsed.path and not parsed.query:
        return None

    match = re.search(r"/san-pham/([^.?#]+?)-(\d+)\.html", parsed.path)
    if match:
        slug, product_id = match.groups()
        return f"https://hasaki.vn/san-pham/{slug}-{product_id}.html"

    query_params = parse_qs(parsed.query)
    keyword = query_params.get("keyword", [None])[0] or query_params.get("q", [None])[0]
    if keyword:
        return f"https://hasaki.vn/tim-kiem.html?keyword={quote(unquote(keyword))}"

    return "https://hasaki.vn" + parsed.path if parsed.path else None


def _normalize_pharmacity_url(raw_url: str) -> Optional[str]:
    parsed = urlparse(raw_url)
    if not _host_matches(parsed.netloc, EXPECTED_HOSTS["Pharmacity"]):
        return None

    if parsed.path.rstrip("/").endswith(("tim-kiem", "search")) and not parsed.query:
        return None

    if parsed.path.endswith(".html"):
        return f"https://www.pharmacity.vn{parsed.path}"

    query_params = parse_qs(parsed.query)
    keyword = query_params.get("keyword", [None])[0]
    if keyword:
        return (
            "https://www.pharmacity.vn/search"
            f"?keyword={quote(unquote(keyword))}&order=desc&order_by=de-xuat"
        )

    source = query_params.get("source", [None])[0]
    if source:
        source_query = parse_qs(urlparse(unquote(source)).query)
        source_keyword = source_query.get("keyword", [None])[0]
        if source_keyword:
            return (
                "https://www.pharmacity.vn/search"
                f"?keyword={quote(unquote(source_keyword))}&order=desc&order_by=de-xuat"
            )

    return "https://www.pharmacity.vn" + parsed.path if parsed.path else None


def _build_search_query(product: models.Product) -> str:
    barcode = (product.barcode or "").strip()
    name = (product.name or "").strip()
    if barcode and name:
        return f"{name} {barcode}"
    return name or barcode


def _mark_normalized(discovery_method: str | None) -> str:
    base = (discovery_method or "manual").strip()
    if "normalized" in base:
        return base
    return f"{base}+normalized"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    collapsed = re.sub(r"[^a-zA-Z0-9]+", " ", ascii_text).strip()
    return re.sub(r"\s+", " ", collapsed)


def _slugify_query(text: str) -> str:
    return _normalize_text(text).replace(" ", "+")


def _host_matches(netloc: str, expected_hosts: tuple[str, ...]) -> bool:
    host = (netloc or "").lower()
    if not host:
        return False
    return any(host == expected or host.endswith(f".{expected}") for expected in expected_hosts)


_NORMALIZERS: dict[str, PlatformNormalizer] = {
    "Shopee": _normalize_shopee_url,
    "Lazada": _normalize_lazada_url,
    "Hasaki": _normalize_hasaki_url,
    "Pharmacity": _normalize_pharmacity_url,
}
