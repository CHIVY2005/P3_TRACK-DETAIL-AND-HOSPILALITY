from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from app.db.session import get_db
from app.db import models
from app import schemas
from app.services.channel_intelligence import build_channel_intelligence
from app.services import response_cache

router = APIRouter()


@router.get("/channel-index", response_model=schemas.ChannelIntelligence)
def get_channel_index(db: Session = Depends(get_db)):
    """Return rubric-grade CPI, coverage, freshness, and promotion metrics per channel."""
    return response_cache.cached("pricing:channel-index", lambda: build_channel_intelligence(db))

@router.get("/visualization")
def get_visualization_data(db: Session = Depends(get_db)):
    """Du lieu cho tab Truc quan hoa: so sanh gia Guardian vs doi thu + chi phi scrape theo kenh."""
    cached = response_cache.get("pricing:visualization")
    if cached is not None:
        return cached

    from app.config import get_scrape_cost_for

    intelligence = build_channel_intelligence(db)

    # Tong chi phi va so lan cao gom theo tung kenh (tren TAT CA ban ghi, khong chi latest).
    cost_rows = (
        db.query(
            models.CompetitorPrice.competitor_name,
            func.count(models.CompetitorPrice.id),
            func.coalesce(func.sum(models.CompetitorPrice.scrape_cost), 0.0),
        )
        .group_by(models.CompetitorPrice.competitor_name)
        .all()
    )
    cost_by_channel = {name: {"count": count, "total": float(total)} for name, count, total in cost_rows}

    channels = []
    for row in intelligence["channels"]:
        name = row["channel"]
        cost = cost_by_channel.get(name, {"count": 0, "total": 0.0})
        channels.append({
            "channel": name,
            "avg_guardian_price": row["avg_guardian_price"],
            "avg_net_price": row["avg_net_price"],
            "cpi": row["cpi"],
            "price_gap_pct": row["price_gap_pct"],
            "scrape_count": cost["count"],
            "scrape_cost_total": round(cost["total"], 2),
            "scrape_cost_unit": get_scrape_cost_for(name),
        })

    result = {
        "channels": channels,
        "totals": {
            "scrape_count": sum(c["scrape_count"] for c in channels),
            "scrape_cost_total": round(sum(c["scrape_cost_total"] for c in channels), 2),
        },
    }
    response_cache.set("pricing:visualization", result)
    return result


@router.get("/overview", response_model=schemas.OverviewStats)
def get_overview_stats(db: Session = Depends(get_db)):
    cached = response_cache.get("pricing:overview")
    if cached is not None:
        return cached

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

    result = schemas.OverviewStats(
        average_cpi=round(average_cpi, 2),
        total_sku=total_sku,
        underpriced_sku=underpriced_sku,
        overpriced_sku=overpriced_sku,
        high_severity_alerts=high_alerts_count,
        category_distribution=cat_distribution,
        competitor_avg_prices=comp_prices
    )
    response_cache.set("pricing:overview", result)
    return result

@router.get("/cpi-index", response_model=List[Dict[str, Any]])
def get_cpi_index_table(db: Session = Depends(get_db)):
    """
    Returns a combined list of products and their corresponding pricing indices and recommendations
    for display in the main dashboard grid.
    """
    cached = response_cache.get("pricing:cpi-index")
    if cached is not None:
        return cached

    from collections import defaultdict
    from app.services.channel_intelligence import get_latest_channel_observations

    products = db.query(models.Product).all()

    # Preload everything the loop needs in a handful of queries instead of ~3 per SKU.
    index_by_product = {idx.product_id: idx for idx in db.query(models.PricingIndex).all()}

    comp_by_product: Dict[int, Dict[str, Any]] = defaultdict(dict)
    for cp in get_latest_channel_observations(db):
        comp_by_product[cp.product_id][cp.competitor_name] = {
            "net_price": cp.net_price,
            "raw_price": cp.raw_price,
            "discount": cp.discount,
            "voucher_details": cp.voucher_details,
            "promo_mechanics": cp.promo_mechanics,
            "url": cp.url,
        }

    alert_counts = dict(
        db.query(models.Alert.product_id, func.count(models.Alert.id))
        .filter(models.Alert.is_resolved == False)
        .group_by(models.Alert.product_id)
        .all()
    )

    result = []
    for p in products:
        idx = index_by_product.get(p.id)
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
            "competitors": comp_by_product.get(p.id, {}),
            "active_alerts": alert_counts.get(p.id, 0),
            "updated_at": idx.updated_at if idx else p.updated_at
        })

    # Sort by active alerts (descending) and then competitor_index deviation from 100
    result.sort(key=lambda x: (x["active_alerts"], abs(100 - x["competitor_index"])), reverse=True)
    response_cache.set("pricing:cpi-index", result)
    return result
