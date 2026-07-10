import re
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models


SEARCH_URL_TEMPLATES = {
    "Shopee": "https://shopee.vn/search?keyword={query}",
    "Lazada": "https://www.lazada.vn/catalog/?q={query}",
    "TikTok Shop": "https://www.tiktok.com/search?q={query}",
    "GrabMart": "https://www.grab.com/vn/food/?q={query}",
    "Pharmacity": "https://www.pharmacity.vn/tim-kiem?q={query}",
    "Hasaki": "https://hasaki.vn/tim-kiem?q={query}",
}


def ensure_competitor_link(db: Session, product: models.Product, platform: str) -> Optional[models.CompetitorLink]:
    existing = (
        db.query(models.CompetitorLink)
        .filter(models.CompetitorLink.product_id == product.id, models.CompetitorLink.platform == platform)
        .first()
    )
    if existing:
        return existing

    query = _slugify_query(product.name or product.barcode)
    template = SEARCH_URL_TEMPLATES.get(platform)
    if not template:
        return None

    link = models.CompetitorLink(
        product_id=product.id,
        platform=platform,
        url=template.format(query=query),
        discovery_method="search-driven",
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def _slugify_query(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact.replace(" ", "+")
