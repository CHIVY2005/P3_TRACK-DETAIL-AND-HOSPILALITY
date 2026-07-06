from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.db import models
from app import schemas
from app.services.cpi_calculator import calculate_cpi_for_product

router = APIRouter()

@router.get("/", response_model=List[schemas.Product])
def list_products(
    skip: int = 0,
    limit: int = 250,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category == category)
    return query.offset(skip).limit(limit).all()

@router.get("/{product_id}", response_model=schemas.ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    return product

@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product_in: schemas.ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Product).filter(models.Product.barcode == product_in.barcode).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with barcode {product_in.barcode} already exists"
        )
    product = models.Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Automatically initialize CPI
    try:
        calculate_cpi_for_product(db, product.id)
    except Exception:
        pass  # suppress error if calculation fails initially
        
    return product

@router.put("/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product_in: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    
    update_data = product_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
        
    db.commit()
    db.refresh(product)
    
    # Recalculate CPI
    calculate_cpi_for_product(db, product.id)
    
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id {product_id} not found"
        )
    db.delete(product)
    db.commit()
    return None


import csv
import io

@router.post("/import-csv", status_code=status.HTTP_201_CREATED)
def import_products_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Dynamically imports a list of products from a CSV file.
    Expected columns: barcode, name, category, guardian_price, cost_price (optional), image_url (optional), description (optional)
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tệp tin tải lên phải có định dạng .csv"
        )
        
    try:
        content = file.file.read().decode("utf-8")
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        
        imported_count = 0
        skipped_count = 0
        
        # Clear existing data for a clean import
        # (This is extremely useful for a hackathon reset)
        db.query(models.Alert).delete()
        db.query(models.PricingIndex).delete()
        db.query(models.CompetitorPrice).delete()
        db.query(models.Product).delete()
        db.commit()
        
        for row in reader:
            barcode = row.get("barcode", "").strip()
            name = row.get("name", "").strip()
            category = row.get("category", "").strip()
            guardian_price_str = row.get("guardian_price", "0").strip()
            
            if not barcode or not name or not category:
                skipped_count += 1
                continue
                
            try:
                guardian_price = float(guardian_price_str)
            except ValueError:
                skipped_count += 1
                continue
                
            # Cost price defaults to 60% if not provided
            cost_price_str = row.get("cost_price", "").strip()
            try:
                cost_price = float(cost_price_str) if cost_price_str else round(guardian_price * 0.60, -3)
            except ValueError:
                cost_price = round(guardian_price * 0.60, -3)
                
            product = models.Product(
                barcode=barcode,
                name=name,
                category=category,
                guardian_price=guardian_price,
                cost_price=cost_price,
                image_url=row.get("image_url", "").strip() or "https://images.unsplash.com/photo-1608248597481-496100c8c836?w=500&auto=format&fit=crop&q=60",
                description=row.get("description", "").strip() or f"{name} phân phối chính hãng tại Guardian."
            )
            db.add(product)
            imported_count += 1
            
        db.commit()
        
        # Automatically trigger scrapers to populate competitor prices for the newly imported skus
        from app.scraper.scraper_engine import scrape_realtime_competitor_prices
        new_products = db.query(models.Product).all()
        for p in new_products:
            try:
                # Runs the scraper pipeline dynamically
                scrape_realtime_competitor_prices(db, p.id)
            except Exception:
                pass
                
        return {
            "status": "success",
            "message": f"Đã nạp thành công {imported_count} sản phẩm mới từ danh sách động. Bỏ qua {skipped_count} dòng lỗi.",
            "imported": imported_count,
            "skipped": skipped_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi đọc file CSV: {str(e)}"
        )
