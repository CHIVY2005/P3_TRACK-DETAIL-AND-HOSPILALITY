import csv
import io
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy.orm import Session

from app.db import models


FIELD_ALIASES = {
    "barcode": ["barcode", "ean", "sku_code", "product_code", "ma_san_pham"],
    "name": ["name", "product_name", "title", "ten_san_pham"],
    "category": ["category", "nganh_hang", "brand_category"],
    "guardian_price": ["guardian_price", "price", "selling_price", "gia_ban"],
    "cost_price": ["cost_price", "cost", "gia_von"],
    "image_url": ["image_url", "image", "thumbnail"],
    "description": ["description", "desc", "mo_ta"],
}

PLATFORM_URL_FIELDS = {
    "Shopee": ["shopee_url", "url_shopee"],
    "Lazada": ["lazada_url", "url_lazada"],
    "TikTok Shop": ["tiktok_url", "tiktok_shop_url", "url_tiktok"],
    "GrabMart": ["grab_url", "grabmart_url", "url_grab"],
    "Pharmacity": ["pharmacity_url", "url_pharmacity"],
    "Hasaki": ["hasaki_url", "url_hasaki"],
}


def import_dataset_from_upload(db: Session, filename: str, raw_content: bytes) -> Dict[str, Any]:
    records = _load_records(filename, raw_content)
    return _import_dataset_records(db, records, filename)


def import_dataset_from_path(db: Session, dataset_path: str) -> Dict[str, Any]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    records = _load_records(path.name, path.read_bytes())
    return _import_dataset_records(db, records, path.name) | {"source_path": str(path)}


def _import_dataset_records(db: Session, records: List[Dict[str, Any]], filename: str) -> Dict[str, Any]:
    normalized = [_normalize_record(record) for record in records]
    valid_rows = []
    validation_errors = []
    seen_barcodes = set()

    for index, row in enumerate(normalized, start=2):
        errors = []
        if not row.get("barcode"):
            errors.append("missing barcode")
        if not row.get("name"):
            errors.append("missing product name")
        if not row.get("category"):
            errors.append("missing category")
        if row.get("guardian_price", 0.0) <= 0:
            errors.append("guardian price must be greater than zero")
        if row.get("barcode") in seen_barcodes:
            errors.append("duplicate barcode in upload")

        if errors:
            validation_errors.append({"row": index, "errors": errors})
            continue

        seen_barcodes.add(row["barcode"])
        valid_rows.append(row)

    if not valid_rows:
        raise ValueError("Dataset contains no valid product rows.")

    skipped = len(normalized) - len(valid_rows)

    _reset_operational_tables(db)

    imported = 0
    competitor_links = 0
    for row in valid_rows:
        product = models.Product(
            barcode=row["barcode"],
            name=row["name"],
            category=row["category"],
            guardian_price=row["guardian_price"],
            cost_price=row["cost_price"],
            image_url=row["image_url"],
            description=row["description"],
        )
        db.add(product)
        db.flush()
        imported += 1

        for platform, url in row["competitor_links"].items():
            if url:
                db.add(
                    models.CompetitorLink(
                        product_id=product.id,
                        platform=platform,
                        url=url,
                        discovery_method="imported",
                    )
                )
                competitor_links += 1

    db.commit()

    return {
        "status": "success",
        "format": "json" if filename.lower().endswith(".json") else "csv",
        "received": len(normalized),
        "imported": imported,
        "skipped": skipped,
        "data_quality_pct": round(imported / len(normalized) * 100.0, 2) if normalized else 0.0,
        "validation_errors": validation_errors[:20],
        "competitor_links": competitor_links,
        "message": f"Imported {imported} products and {competitor_links} competitor links.",
    }


def _load_records(filename: str, raw_content: bytes) -> List[Dict[str, Any]]:
    if filename.lower().endswith(".json"):
        payload = json.loads(raw_content.decode("utf-8-sig"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        raise ValueError("JSON payload must contain an array of product objects.")

    if filename.lower().endswith(".csv"):
        content = raw_content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(content)))

    raise ValueError("Uploaded file must be a .csv or .json dataset.")


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "barcode": _pick_first(record, FIELD_ALIASES["barcode"]),
        "name": _pick_first(record, FIELD_ALIASES["name"]),
        "category": _pick_first(record, FIELD_ALIASES["category"]) or "Uncategorized",
        "guardian_price": _parse_price(_pick_first(record, FIELD_ALIASES["guardian_price"]), default=0.0),
        "cost_price": None,
        "image_url": _pick_first(record, FIELD_ALIASES["image_url"]) or "https://images.unsplash.com/photo-1608248597481-496100c8c836?w=500&auto=format&fit=crop&q=60",
        "description": _pick_first(record, FIELD_ALIASES["description"]),
        "competitor_links": {},
    }

    cost_price = _parse_price(_pick_first(record, FIELD_ALIASES["cost_price"]), default=None)
    normalized["cost_price"] = cost_price if cost_price is not None else round(normalized["guardian_price"] * 0.60, -3)
    if not normalized["description"]:
        normalized["description"] = f"{normalized['name']} distributed at Guardian."

    for platform, aliases in PLATFORM_URL_FIELDS.items():
        url = _pick_first(record, aliases)
        if url:
            normalized["competitor_links"][platform] = url

    return normalized


def _pick_first(record: Dict[str, Any], aliases: Iterable[str]) -> str:
    lowered = {str(key).strip().lower(): value for key, value in record.items()}
    for alias in aliases:
        value = lowered.get(alias.lower())
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _parse_price(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default

    cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch in {".", ","})
    if not cleaned:
        return default

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
        return default


def _reset_operational_tables(db: Session) -> None:
    db.query(models.AgentAction).delete()
    db.query(models.AgentTask).delete()
    db.query(models.Alert).delete()
    db.query(models.PricingIndex).delete()
    db.query(models.CompetitorPrice).delete()
    if hasattr(models, "CompetitorLink"):
        db.query(models.CompetitorLink).delete()
    db.query(models.Product).delete()
