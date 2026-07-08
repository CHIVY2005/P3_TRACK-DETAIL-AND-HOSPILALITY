import csv
import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import models
from app.services.cpi_calculator import calculate_all_cpi


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _parse_float(value: str):
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    return float(raw)


def seed_demo_dataset(db: Session) -> dict:
    project_root = _project_root()
    sku_path = os.path.join(project_root, "data", "sku_master.csv")
    competitor_path = os.path.join(project_root, "data", "competitor_mock.csv")

    if not os.path.exists(sku_path) or not os.path.exists(competitor_path):
        raise FileNotFoundError("Demo CSV dataset is missing from the data directory.")

    db.query(models.AgentAction).delete()
    db.query(models.AgentTask).delete()
    db.query(models.Alert).delete()
    db.query(models.PricingIndex).delete()
    db.query(models.CompetitorPrice).delete()
    db.query(models.Product).delete()
    db.commit()

    imported_products = 0
    imported_prices = 0

    with open(sku_path, "r", encoding="utf-8") as sku_file:
        for row in csv.DictReader(sku_file):
            product = models.Product(
                id=int(row["id"]),
                barcode=row["barcode"].strip(),
                name=row["name"].strip(),
                category=row["category"].strip(),
                guardian_price=float(row["guardian_price"]),
                cost_price=float(row["cost_price"]),
                image_url=(row.get("image_url") or "").strip() or None,
                description=(row.get("description") or "").strip() or None,
            )
            db.add(product)
            imported_products += 1
    db.commit()

    with open(competitor_path, "r", encoding="utf-8") as competitor_file:
        for row in csv.DictReader(competitor_file):
            price = models.CompetitorPrice(
                product_id=int(row["product_id"]),
                competitor_name=row["competitor_name"].strip(),
                raw_price=_parse_float(row.get("raw_price")),
                discount=_parse_float(row.get("discount")) or 0.0,
                net_price=_parse_float(row.get("net_price")),
                stock_status=(row.get("stock_status") or "IN_STOCK").strip(),
                is_suspicious=str(row.get("is_suspicious", "")).strip().lower() == "true",
                voucher_details=(row.get("voucher_details") or "").strip() or None,
                promo_mechanics=(row.get("promo_mechanics") or "").strip() or None,
                url=(row.get("url") or "").strip() or None,
                scraped_at=datetime.strptime(row["scraped_at"], "%Y-%m-%d %H:%M:%S"),
            )
            db.add(price)
            imported_prices += 1
    db.commit()

    calculate_all_cpi(db)

    return {
        "products": imported_products,
        "competitor_prices": imported_prices,
        "source": {
            "sku_master": sku_path,
            "competitor_prices": competitor_path,
        },
    }
