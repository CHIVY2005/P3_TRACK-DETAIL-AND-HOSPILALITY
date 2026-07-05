import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models import Product, CompetitorPrice
from app.services.cpi_calculator import calculate_cpi_for_product

# List of competitor channels to scrape
COMPETITORS = ["Shopee", "Lazada", "TikTok Shop", "GrabMart", "Pharmacity"]

def scrape_realtime_competitor_prices(db: Session, product_id: int) -> list:
    """
    Mock scraper function.
    In a real implementation, you would:
    1. Retrieve the product barcode/URL.
    2. Query an API (e.g., Apify, Shopee API) or scrape the site using requests/Playwright.
    3. Parse the price, discount, vouchers, and promo mechanics.
    4. Return the structured data.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return []

    new_prices = []
    
    # Simulate scraping for each competitor
    for competitor in COMPETITORS:
        # Determine pricing characteristics per platform
        if competitor == "Shopee":
            # Shopee is often cheaper, highly active promos
            price_factor = random.uniform(0.82, 0.98)
            discount_pct = random.choice([0.0, 0.05, 0.10, 0.15])
            voucher = random.choice([None, "Mã giảm 10k", "Mã giảm 20k", "Freeship Extra"])
            promo = random.choice([None, "Mua kèm deal sốc", "Flash Sale"])
        elif competitor == "Lazada":
            # Lazada is competitive, moderate promos
            price_factor = random.uniform(0.85, 0.97)
            discount_pct = random.choice([0.0, 0.05, 0.08, 0.12])
            voucher = random.choice([None, "Voucher tích lũy", "Mã giảm 15k"])
            promo = random.choice([None, "Combo mua 2 giảm 5%", "Flash Sale"])
        elif competitor == "TikTok Shop":
            # TikTok Shop has extreme flash sales and livestream vouchers
            price_factor = random.uniform(0.78, 0.95)
            discount_pct = random.choice([0.0, 0.10, 0.20])
            voucher = random.choice([None, "Voucher Livestream 25k", "Mã người mới"])
            promo = random.choice([None, "Flash Sale hàng hiệu"])
        elif competitor == "GrabMart":
            # GrabMart is usually convenience priced, so more expensive
            price_factor = random.uniform(0.98, 1.15)
            discount_pct = 0.0
            voucher = None
            promo = None
        else:  # Pharmacity / competitor website
            # Web competitor, stable pricing close to Guardian
            price_factor = random.uniform(0.95, 1.05)
            discount_pct = random.choice([0.0, 0.05])
            voucher = None
            promo = None

        # Calculations
        raw_price = round(product.guardian_price * price_factor, -3) # round to nearest thousands
        
        # Calculate discount amount
        discount_amount = round(raw_price * discount_pct, -3)
        
        # Calculate net price
        net_price = raw_price - discount_amount
        
        # Voucher discount deduction (if voucher exists)
        voucher_val = 0
        if voucher:
            if "10k" in voucher:
                voucher_val = 10000
            elif "15k" in voucher:
                voucher_val = 15000
            elif "20k" in voucher:
                voucher_val = 20000
            elif "25k" in voucher:
                voucher_val = 25000
            
            # Net price after voucher
            net_price = max(1000, net_price - voucher_val)

        # Mock competitor URL
        comp_slug = competitor.lower().replace(" ", "")
        mock_url = f"https://www.{comp_slug}.vn/search?q={product.barcode}"

        # Create price record
        price_record = CompetitorPrice(
            product_id=product.id,
            competitor_name=competitor,
            raw_price=raw_price,
            discount=discount_amount,
            net_price=net_price,
            voucher_details=voucher,
            promo_mechanics=promo,
            url=mock_url,
            scraped_at=datetime.utcnow()
        )
        db.add(price_record)
        new_prices.append(price_record)

    db.commit()
    
    # Recalculate CPI for the product after new data points added
    calculate_cpi_for_product(db, product.id)
    
    return new_prices

def run_scraper_for_all_products(db: Session):
    products = db.query(Product).all()
    results = {}
    for p in products:
        results[p.id] = scrape_realtime_competitor_prices(db, p.id)
    return results
