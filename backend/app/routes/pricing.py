from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.db.session import get_db
from app.db import models
from app import schemas

router = APIRouter()

@router.get("/overview", response_model=schemas.OverviewStats)
def get_overview_stats(db: Session = Depends(get_db)):
    # 1. Fetch total products
    total_sku = db.query(models.Product).count()
    if total_sku == 0:
        return schemas.OverviewStats(
            average_cpi=100.0,
            total_sku=0,
            underpriced_sku=0,
            overpriced_sku=0,
            high_severity_alerts=0,
            category_distribution={},
            competitor_avg_prices={}
        )

    # 2. Fetch CPI statistics
    indices = db.query(models.PricingIndex).all()
    cpi_values = [idx.competitor_index for idx in indices]
    average_cpi = sum(cpi_values) / len(cpi_values) if cpi_values else 100.0

    # Count under/overpriced based on standard 90/110 thresholds
    underpriced_sku = sum(1 for cpi in cpi_values if cpi < 90.0)
    overpriced_sku = sum(1 for cpi in cpi_values if cpi > 110.0)

    # 3. Fetch active high-severity alerts
    high_alerts_count = db.query(models.Alert).filter(
        models.Alert.is_resolved == False,
        models.Alert.severity == "High"
    ).count()

    # 4. Fetch category distribution
    cat_distribution = {}
    cat_query = db.query(
        models.Product.category,
        func.count(models.Product.id)
    ).group_by(models.Product.category).all()
    for cat, count in cat_query:
        cat_distribution[cat] = count

    # 5. Fetch competitor average prices
    comp_prices = {}
    comp_query = db.query(
        models.CompetitorPrice.competitor_name,
        func.avg(models.CompetitorPrice.net_price)
    ).group_by(models.CompetitorPrice.competitor_name).all()
    for name, avg in comp_query:
        comp_prices[name] = round(avg, 2)

    return schemas.OverviewStats(
        average_cpi=round(average_cpi, 2),
        total_sku=total_sku,
        underpriced_sku=underpriced_sku,
        overpriced_sku=overpriced_sku,
        high_severity_alerts=high_alerts_count,
        category_distribution=cat_distribution,
        competitor_avg_prices=comp_prices
    )

@router.get("/cpi-index", response_model=List[Dict[str, Any]])
def get_cpi_index_table(db: Session = Depends(get_db)):
    """
    Returns a combined list of products and their corresponding pricing indices and recommendations
    for display in the main dashboard grid.
    """
    products = db.query(models.Product).all()
    result = []
    
    for p in products:
        # Get latest pricing index
        idx = db.query(models.PricingIndex).filter(models.PricingIndex.product_id == p.id).first()
        
        # Get latest competitor prices
        # First, find the max scraped date per competitor for this product
        subq = db.query(
            models.CompetitorPrice.competitor_name,
            func.max(models.CompetitorPrice.scraped_at).label("max_scraped")
        ).filter(models.CompetitorPrice.product_id == p.id).group_by(models.CompetitorPrice.competitor_name).subquery()
        
        comp_prices = db.query(models.CompetitorPrice).join(
            subq,
            (models.CompetitorPrice.competitor_name == subq.c.competitor_name) &
            (models.CompetitorPrice.scraped_at == subq.c.max_scraped)
        ).filter(models.CompetitorPrice.product_id == p.id).all()
        
        comp_data = {}
        for cp in comp_prices:
            comp_data[cp.competitor_name] = {
                "net_price": cp.net_price,
                "raw_price": cp.raw_price,
                "discount": cp.discount,
                "voucher_details": cp.voucher_details,
                "promo_mechanics": cp.promo_mechanics,
                "url": cp.url
            }

        # Calculate count of unresolved alerts
        alert_count = db.query(models.Alert).filter(
            models.Alert.product_id == p.id,
            models.Alert.is_resolved == False
        ).count()

        result.append({
            "id": p.id,
            "barcode": p.barcode,
            "name": p.name,
            "category": p.category,
            "guardian_price": p.guardian_price,
            "image_url": p.image_url,
            "competitor_index": idx.competitor_index if idx else 100.0,
            "average_competitor_price": idx.average_competitor_price if idx else p.guardian_price,
            "recommendation": idx.recommendation if idx else "Maintain Price",
            "competitors": comp_data,
            "active_alerts": alert_count,
            "updated_at": idx.updated_at if idx else p.updated_at
        })
        
    # Sort by active alerts (descending) and then competitor_index deviation from 100
    result.sort(key=lambda x: (x["active_alerts"], abs(100 - x["competitor_index"])), reverse=True)
    return result
