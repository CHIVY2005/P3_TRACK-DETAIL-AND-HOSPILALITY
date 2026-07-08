import json
import os
import re
from typing import List

from sqlalchemy.orm import Session

from app.db import models


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _normalize(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    return [token for token in cleaned.split() if len(token) > 2]


def _best_catalog_match(db: Session, title: str):
    title_tokens = set(_normalize(title))
    if not title_tokens:
        return None

    best_product = None
    best_score = 0
    for product in db.query(models.Product).limit(250).all():
        product_tokens = set(_normalize(product.name))
        overlap = len(title_tokens & product_tokens)
        if overlap > best_score:
            best_score = overlap
            best_product = product

    if not best_product or best_score < 2:
        return None

    return {
        "product_id": best_product.id,
        "product_name": best_product.name,
        "guardian_price": best_product.guardian_price,
        "category": best_product.category,
    }


def load_branch_scrape_samples(db: Session) -> List[dict]:
    project_root = _project_root()
    samples = []

    datasets = [
        {
            "path": os.path.join(project_root, "dataset_shopee-scraper_2026-07-06_05-01-14-978.json"),
            "source": "branch_of_Duy",
            "platform": "Shopee",
            "kind": "real_sample",
        },
        {
            "path": os.path.join(project_root, "dataset_shopee-scraper_2026-07-06_04-32-31-501.json"),
            "source": "branch_of_Duy",
            "platform": "Shopee",
            "kind": "mock_batch",
        },
    ]

    for dataset in datasets:
        if not os.path.exists(dataset["path"]):
            continue

        with open(dataset["path"], "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if not payload:
            continue

        first = payload[0]
        title = first.get("title") or first.get("name") or "Unknown item"
        current_price = first.get("price")
        original_price = first.get("price_before_discount") or first.get("originalPrice")
        discount_pct = first.get("discount_pct") or first.get("discountPercent")
        item_url = None
        if first.get("breadcrumb"):
            item_url = first["breadcrumb"][-1].get("url")
        item_url = item_url or first.get("url")

        samples.append(
            {
                "source": dataset["source"],
                "platform": dataset["platform"],
                "kind": dataset["kind"],
                "title": title,
                "brand": first.get("brand"),
                "current_price": current_price,
                "original_price": original_price,
                "discount_pct": discount_pct,
                "rating": first.get("rating_star") or first.get("rating"),
                "url": item_url,
                "record_count": len(payload),
                "match": _best_catalog_match(db, title),
            }
        )

    return samples
