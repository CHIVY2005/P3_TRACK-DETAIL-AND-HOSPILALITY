from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.session import get_db
from app.services.cpi_calculator import calculate_cpi_for_product
from app.services.data_ingestion import import_dataset_from_upload
from app.services.demo_seed import seed_demo_dataset
from app.services import response_cache

router = APIRouter()


@router.get("/", response_model=List[schemas.Product])
def list_products(
    skip: int = 0,
    limit: int = 250,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category == category)
    return query.offset(skip).limit(limit).all()


@router.get("/{product_id:int}", response_model=schemas.ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )
    return product


@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product_in: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Product).filter(models.Product.barcode == product_in.barcode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with barcode {product_in.barcode} already exists",
        )

    product = models.Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    try:
        calculate_cpi_for_product(db, product.id)
    except Exception:
        pass

    return product


@router.put("/{product_id:int}", response_model=schemas.Product)
def update_product(product_id: int, product_in: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    calculate_cpi_for_product(db, product.id)
    return product


@router.delete("/{product_id:int}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found",
        )

    db.delete(product)
    db.commit()
    return None


@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
def import_products_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = file.file.read()
        result = import_dataset_from_upload(db, file.filename or "", content)
        response_cache.invalidate_all()
        return result | {
            "message": (
                f"Imported {result['imported']} products and registered {result['competitor_links']} competitor links. "
                "The catalog is ready for the daily scheduler or a manual channel refresh."
            )
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import CSV: {exc}",
        )


@router.post("/import-dataset", status_code=status.HTTP_201_CREATED)
def import_products_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return import_products_csv(file, db)


@router.post("/seed-demo", status_code=status.HTTP_201_CREATED)
def seed_demo_data(db: Session = Depends(get_db)):
    try:
        result = seed_demo_dataset(db)
        response_cache.invalidate_all()
        return {
            "status": "success",
            "message": f"Loaded {result['products']} demo SKUs and {result['competitor_prices']} competitor price records.",
            **result,
        }
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed demo dataset: {exc}",
        )
