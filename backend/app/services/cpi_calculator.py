from sqlalchemy.orm import Session
from app.db.models import Product, CompetitorPrice, PricingIndex, Alert
from app.config import get_agent_config
from app.services.channel_intelligence import get_latest_channel_observations

def calculate_cpi_for_product(db: Session, product_id: int, commit: bool = True) -> PricingIndex:
    # 1. Fetch product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # 2. Fetch one deterministic latest observation per competitor channel.
    latest_prices = get_latest_channel_observations(db, product_id=product_id)

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
            cfg = get_agent_config()
            overprice_limit = 100.0 * (1.0 + cfg.get("overprice_threshold", 0.10))
            underprice_limit = 100.0 * (1.0 - cfg.get("underprice_threshold", 0.10))

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
    
    if commit:
        db.commit()
        db.refresh(index_record)
    else:
        db.flush()

    # 4. Generate alerts based on prices
    generate_alerts_for_product(db, product, latest_prices, cpi, commit=commit)

    return index_record

def generate_alerts_for_product(db: Session, product: Product, latest_prices: list, cpi: float, commit: bool = True):
    # Clear unacknowledged/unresolved alerts for this product first to avoid cluttering
    db.query(Alert).filter(Alert.product_id == product.id, Alert.is_resolved == False).delete()
    if commit:
        db.commit()
    else:
        db.flush()

    cfg = get_agent_config()
    underprice_threshold = cfg.get("underprice_threshold", 0.10)
    overprice_threshold = cfg.get("overprice_threshold", 0.10)
    overprice_limit = 100.0 * (1.0 + overprice_threshold)
    underprice_limit = 100.0 * (1.0 - underprice_threshold)

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
        if cheaper_ratio > underprice_threshold:
            db.add(Alert(
                product_id=product.id,
                alert_type="Competitor Undercutting",
                message=f"Competitor {cp.competitor_name} is selling below Guardian by {cheaper_ratio * 100:.1f}% (Net Price: {cp.net_price:,.0f} VND vs Guardian: {product.guardian_price:,.0f} VND).",
                severity="High" if cheaper_ratio > 0.20 else "Medium"
            ))

    if commit:
        db.commit()
    else:
        db.flush()

def calculate_all_cpi(db: Session):
    products = db.query(Product).all()
    for product in products:
        calculate_cpi_for_product(db, product.id, commit=False)
    db.commit()

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
