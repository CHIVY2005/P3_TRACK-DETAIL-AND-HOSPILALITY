import datetime
import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ingestion"])

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "app" / "core" / "mapping_config.json"
DATA_DIR = BASE_DIR / "data"


def clean_price(val: Any) -> Optional[int]:
    """Normalize a price field to an integer while preserving currency value."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int,)):
        return int(val)
    if isinstance(val, float):
        return int(round(val))

    text = str(val).strip()
    text = re.sub(r"([.,])(\d{1,2})$", "", text)
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


@router.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = DATA_DIR / safe_filename

        contents = file.file.read()
        file.file.close()
        file_path.write_bytes(contents)

        if file.filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
        elif file.filename.lower().endswith(".json"):
            df = pd.read_json(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use .csv or .json.")

        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            mapping_config = json.load(f)

        rename_map = {}
        for config_key, raw_headers in mapping_config.items():
            raw_headers_lower = {str(h).strip().lower() for h in raw_headers}
            if config_key == "barcode":
                target_col = "barcode"
            elif config_key == "product_name":
                target_col = "product_name"
            elif config_key == "price":
                target_col = "guardian_price"
            else:
                continue

            for col in df.columns:
                if str(col).strip().lower() in raw_headers_lower:
                    rename_map[col] = target_col
                    break

        df.rename(columns=rename_map, inplace=True)

        if "guardian_price" not in df.columns and "price" in df.columns:
            df.rename(columns={"price": "guardian_price"}, inplace=True)
        if "category" not in df.columns:
            df["category"] = "Unknown"

        required_cols = ["barcode", "product_name", "category", "guardian_price"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Missing required columns after mapping: {missing_cols}")

        df = df[required_cols].copy()
        df["barcode"] = df["barcode"].astype(str).str.strip()
        df["product_name"] = df["product_name"].astype(str).str.strip()
        df["category"] = df["category"].astype(str).str.strip().replace("", "Unknown")
        df["guardian_price"] = df["guardian_price"].apply(clean_price)

        df.replace({"": pd.NA}, inplace=True)
        df.dropna(subset=["barcode", "product_name", "category", "guardian_price"], inplace=True)
        df["guardian_price"] = df["guardian_price"].astype(int)

        records = df.to_dict(orient="records")
        if not records:
            raise HTTPException(status_code=400, detail="No valid records left to insert after processing.")

        stmt = insert(models.SkuMaster.__table__).values(records)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["barcode"],
            set_={
                "product_name": stmt.excluded.product_name,
                "category": stmt.excluded.category,
                "guardian_price": stmt.excluded.guardian_price,
            },
        )

        db.execute(upsert_stmt)
        db.commit()

        return {
            "status": "success",
            "file_saved": safe_filename,
            "processed_records": len(records),
            "upsert_target": "sku_master",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during ingestion")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

