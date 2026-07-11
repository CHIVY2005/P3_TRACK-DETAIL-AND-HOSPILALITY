import io
import json
import logging
import re
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.data_ingestion import import_dataset_from_upload


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ingestion"])

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "app" / "core" / "mapping_config.json"
DATA_DIR = BASE_DIR / "data"


def _load_mapping_config() -> Dict[str, list[str]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _match_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized_columns = {str(col).strip().lower(): col for col in columns}
    normalized_candidates = [str(candidate).strip().lower() for candidate in candidates]

    for candidate in normalized_candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    for column in columns:
        column_key = str(column).strip().lower()
        if get_close_matches(column_key, normalized_candidates, n=1, cutoff=0.82):
            return column

    return None


def _safe_filename(filename: str | None) -> str:
    base = Path(filename or "upload.csv").name
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", base)


def _normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    mapping_config = _load_mapping_config()
    rename_map: Dict[str, str] = {}

    core_targets = {
        "barcode": "barcode",
        "product_name": "name",
        "price": "guardian_price",
    }

    for config_key, raw_headers in mapping_config.items():
        target_col = core_targets.get(config_key)
        if not target_col:
            continue
        matched = _match_column(list(df.columns), raw_headers)
        if matched:
            rename_map[matched] = target_col

    df = df.rename(columns=rename_map).copy()

    if "guardian_price" not in df.columns and "price" in df.columns:
        df.rename(columns={"price": "guardian_price"}, inplace=True)
    if "name" not in df.columns and "product_name" in df.columns:
        df.rename(columns={"product_name": "name"}, inplace=True)
    if "category" not in df.columns:
        df["category"] = "Unknown"

    return df


@router.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = _safe_filename(file.filename)
        saved_path = DATA_DIR / f"{timestamp}_{filename}"

        contents = file.file.read()
        file.file.close()
        saved_path.write_bytes(contents)

        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
        elif filename.lower().endswith(".json"):
            payload = json.loads(contents.decode("utf-8-sig"))
            if isinstance(payload, list):
                df = pd.DataFrame(payload)
            elif isinstance(payload, dict):
                df = pd.DataFrame(payload)
            else:
                raise HTTPException(status_code=400, detail="Invalid JSON upload payload.")
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use .csv or .json.")

        normalized_df = _normalize_dataframe(df)
        normalized_df = normalized_df.replace({"": pd.NA})

        if "guardian_price" in normalized_df.columns:
            normalized_df["guardian_price"] = normalized_df["guardian_price"].astype(str)

        export_buffer = io.BytesIO()
        if filename.lower().endswith(".csv"):
            normalized_df.to_csv(export_buffer, index=False)
            normalized_bytes = export_buffer.getvalue()
            normalized_name = filename
        else:
            normalized_name = filename
            normalized_bytes = json.dumps(
                normalized_df.where(pd.notna(normalized_df), None).to_dict(orient="records"),
                ensure_ascii=False,
            ).encode("utf-8")

        result = import_dataset_from_upload(db, normalized_name, normalized_bytes)
        return {
            "status": "success",
            "file_saved": saved_path.name,
            "mapped_columns": list(normalized_df.columns),
            **result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error during ingestion")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
