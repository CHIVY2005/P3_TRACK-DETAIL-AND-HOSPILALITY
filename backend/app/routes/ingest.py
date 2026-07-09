import os
import json
import io
import datetime
import logging
import pandas as pd
import re
from typing import Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.core.config import settings

# Assume get_db dependency and sku_master Table/Model exist in your app
from app.db.session import get_db
from app.models.sku import sku_master 

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["Ingestion"])

CONFIG_PATH = "backend/app/core/mapping_config.json"
DATA_DIR = "backend/data/"

def clean_price(val: Any) -> Optional[float]:
    """Helper to clean price data (currency chars, commas, etc)"""
    if pd.isna(val):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    cleaned = re.sub(r'[^\d.]', '', str(val).replace(',', '.'))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    try:
        # 1. Save raw file copy to backend/data/
        os.makedirs(DATA_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(DATA_DIR, safe_filename)

        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
            
        # 2. Parse via Pandas DataFrame
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith('.json'):
            df = pd.read_json(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use .csv or .json.")

        # 3. Dynamic map columns using mapping_config.json
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            mapping_config = json.load(f)

        target_mapping = {
            "barcode_col": "barcode",
            "name_col": "product_name",
            "price_col": "price"
        }

        rename_map = {}
        for config_key, raw_headers in mapping_config.items():
            db_col = target_mapping.get(config_key)
            if not db_col:
                continue
                
            raw_headers_lower = [str(h).lower() for h in raw_headers]
            for col in df.columns:
                if str(col).strip().lower() in raw_headers_lower:
                    rename_map[col] = db_col
                    break

        df.rename(columns=rename_map, inplace=True)
        
        required_cols = {"barcode", "product_name", "price"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Missing mapped required columns: {missing_cols}")

        df = df[list(required_cols)]

        df['barcode'] = df['barcode'].astype(str).str.strip()
        df['product_name'] = df['product_name'].astype(str).str.strip()
        df['price'] = df['price'].apply(clean_price)
        
        df.dropna(subset=['barcode', 'price'], inplace=True)
        
        records = df.to_dict(orient="records")
        if not records:
            raise HTTPException(status_code=400, detail="No valid records left to insert after processing.")

        # 4. Perform SQLAlchemy Core UPSERT into sku_master
        stmt = insert(sku_master).values(records)
        
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['barcode'],
            set_={
                'product_name': stmt.excluded.product_name,
                'price': stmt.excluded.price
            }
        )
        
        await db.execute(upsert_stmt)
        await db.commit()

        return {
            "status": "success",
            "file_saved": safe_filename,
            "processed_records": len(records)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
