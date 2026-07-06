from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Product, CompetitorPrice, PricingIndex, Alert
from app.config import settings

def calculate_cpi_for_product(db: Session, product_id: int) -> PricingIndex:
    # 1. Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # 2. Fetch latest competitor prices (grouped by competitor_name, taking the most recent scrape)
    # For a simple boilerplate, we take all competitor prices in the last run or just the latest entries.
    # Let's query the latest price for each competitor name for this product
    subquery = db.query(
        CompetitorPrice.competitor_name,
        func.max(CompetitorPrice.scraped_at).label("max_scraped_at")
    ).filter(CompetitorPrice.product_id == product_id).group_by(CompetitorPrice.competitor_name).subquery()

    latest_prices = db.query(CompetitorPrice).join(
        subquery,
        (CompetitorPrice.competitor_name == subquery.c.competitor_name) & 
        (CompetitorPrice.scraped_at == subquery.c.max_scraped_at)
    ).filter(CompetitorPrice.product_id == product_id).all()

    if not latest_prices:
        # No competitor prices, default to neutral
        cpi = 100.0
        avg_price = product.guardian_price
        recommendation = "Maintain Price"
    else:
        # Filter out competitors that are OUT_OF_STOCK, have no net_price, or are marked suspicious
        in_stock_prices = [item.net_price for item in latest_prices if item.stock_status != "OUT_OF_STOCK" and item.net_price is not None and not item.is_suspicious]
        
        if in_stock_prices:
            avg_price = sum(in_stock_prices) / len(in_stock_prices)
            if avg_price > 0:
                cpi = (product.guardian_price / avg_price) * 100
            else:
                cpi = 100.0
            
            # Determine recommendation based on thresholds
            overprice_limit = 100.0 * (1.0 + settings.ALERT_OVERPRICE_THRESHOLD)
            underprice_limit = 100.0 * (1.0 - settings.ALERT_UNDERPRICE_THRESHOLD)

            if cpi > overprice_limit:
                recommendation = "Lower Price"
            elif cpi < underprice_limit:
                recommendation = "Increase Price"
            else:
                recommendation = "Maintain Price"
        else:
            # All competitors are OUT_OF_STOCK!
            # Retail Intelligence: Maintain Price (No competition pressure)
            cpi = 100.0
            avg_price = product.guardian_price
            recommendation = "Maintain Price (Competitors OOS)"

    # 3. Create or update pricing index
    index_record = db.query(PricingIndex).filter(PricingIndex.product_id == product_id).first()
    if not index_record:
        index_record = PricingIndex(product_id=product_id)
        db.add(index_record)

    index_record.competitor_index = round(cpi, 2)
    index_record.average_competitor_price = round(avg_price, 2)
    index_record.recommendation = recommendation
    db.commit()
    db.refresh(index_record)

    # 4. Generate alerts based on prices
    generate_alerts_for_product(db, product, latest_prices, cpi)

    return index_record

def generate_alerts_for_product(db: Session, product: Product, latest_prices: list, cpi: float):
    # Clear unacknowledged/unresolved alerts for this product first to avoid cluttering
    db.query(Alert).filter(Alert.product_id == product.id, Alert.is_resolved == False).delete()
    db.commit()

    overprice_limit = 100.0 * (1.0 + settings.ALERT_OVERPRICE_THRESHOLD)
    underprice_limit = 100.0 * (1.0 - settings.ALERT_UNDERPRICE_THRESHOLD)

    # Threshold alerts based on overall CPI
    if cpi > overprice_limit:
        difference_pct = cpi - 100.0
        db.add(Alert(
            product_id=product.id,
            alert_type="Overpriced",
            message=f"Guardian price ({product.guardian_price:,.0f} VND) is {difference_pct:.1f}% higher than competitor average ({product.guardian_price * 100 / cpi:,.0f} VND).",
            severity="Medium"
        ))
    elif cpi < underprice_limit:
        difference_pct = 100.0 - cpi
        db.add(Alert(
            product_id=product.id,
            alert_type="Underpriced",
            message=f"Guardian price ({product.guardian_price:,.0f} VND) is {difference_pct:.1f}% lower than competitor average. Potential margin leakage, consider raising price.",
            severity="Medium"
        ))

    # Competitor-specific severe undercutting alerts
    for cp in latest_prices:
        if cp.stock_status == "OUT_OF_STOCK" or cp.net_price is None or cp.is_suspicious:
            continue
        # If competitor is much cheaper than Guardian
        if product.guardian_price > 0:
            cheaper_ratio = (product.guardian_price - cp.net_price) / product.guardian_price
        else:
            cheaper_ratio = 0.0
        if cheaper_ratio > settings.ALERT_UNDERPRICE_THRESHOLD:
            db.add(Alert(
                product_id=product.id,
                alert_type="Competitor Undercutting",
                message=f"Competitor {cp.competitor_name} is selling below Guardian by {cheaper_ratio * 100:.1f}% (Net Price: {cp.net_price:,.0f} VND vs Guardian: {product.guardian_price:,.0f} VND).",
                severity="High" if cheaper_ratio > 0.20 else "Medium"
            ))

    db.commit()

def calculate_all_cpi(db: Session):
    products = db.query(Product).all()
    for product in products:
        calculate_cpi_for_product(db, product.id)

def check_price_anomaly(db: Session, product_id: int, competitor_name: str, new_net_price: float) -> bool:
    """
    Compares the newly scraped price against the historical average net price for this competitor and product.
    If the price deviates by more than 50% from the historical average, it is marked as suspicious.
    """
    if new_net_price is None or new_net_price <= 0:
        return False
        
    # Get last 10 non-suspicious historical prices for this competitor and product
    history = db.query(CompetitorPrice).filter(
        CompetitorPrice.product_id == product_id,
        CompetitorPrice.competitor_name == competitor_name,
        CompetitorPrice.is_suspicious == False,
        CompetitorPrice.net_price.isnot(None)
    ).order_by(CompetitorPrice.scraped_at.desc()).limit(10).all()
    
    if not history:
        return False # No history to compare against, trust the new price
        
    # Calculate historical average
    avg_history_price = sum(item.net_price for item in history) / len(history)
    
    if avg_history_price <= 0:
        return False
        
    # Check for anomaly (deviation > 50% down or > 50% up)
    deviation = abs(new_net_price - avg_history_price) / avg_history_price
    if deviation > 0.50:
        return True # Anomaly detected!
        
    return False
