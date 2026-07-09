from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.db.models import CompetitorLink, SkuMaster


def discover_competitor_link(barcode: str, product_name: str, db: Session, platform: str = "Shopee") -> str:
    """Return an existing competitor URL or create a safe fallback search URL."""
    sku = db.query(SkuMaster).filter(SkuMaster.barcode == barcode).first()
    if not sku:
        raise ValueError(f"SKU {barcode} was not found in sku_master.")

    existing = (
        db.query(CompetitorLink)
        .filter(CompetitorLink.barcode == barcode, CompetitorLink.platform == platform)
        .first()
    )
    if existing:
        return existing.url

    fallback_url = f"https://shopee.vn/search?keyword={quote_plus(product_name)}"
    new_link = CompetitorLink(
        barcode=barcode,
        platform=platform,
        url=fallback_url,
        platform_item_id=None,
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    return fallback_url
