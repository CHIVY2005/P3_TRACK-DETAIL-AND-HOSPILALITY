import os
import sys
import random
import csv
import argparse
from datetime import datetime, timedelta

# Adjust python path to import app modules if running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# Real-world brand templates for Vietnam health/beauty market
BRANDS = {
    "Skincare": ["La Roche-Posay", "Vichy", "Bioderma", "Anessa", "Cosrx", "Senka", "Klairs", "Some By Mi", "Innisfree", "L'Oreal Paris", "CeraVe", "Eucerin"],
    "Makeup": ["Maybelline New York", "3CE", "Black Rouge", "Romand", "L'Oreal Paris", "MAC", "Estee Lauder", "Focallure", "Merzy", "Lemonade"],
    "Personal Care": ["Dove", "Sunsilk", "Pantene", "Head & Shoulders", "Lifebuoy", "Nivea", "Rexona", "Colgate", "Sensodyne", "Listerine", "Enchanteur", "TRESemme"],
    "Health & Wellness": ["Blackmores", "DHC", "Kirkland Signature", "Nature's Way", "Panadol", "Strepsils", "Salonpas", "Durex", "Mega We Care", "Optimum Nutrition"]
}

PRODUCT_TYPES = {
    "Skincare": [
        ("Kem Chống Nắng", 150000, 650000, "Kem chống nắng bảo vệ da tối ưu dưới ánh nắng mặt trời."),
        ("Nước Tẩy Trang", 80, 500, "Nước tẩy trang làm sạch sâu, dịu nhẹ cho mọi loại da."),
        ("Sữa Rửa Mặt", 80000, 350000, "Sữa rửa mặt tạo bọt mịn giúp làm sạch bụi bẩn và bã nhờn."),
        ("Serum Dưỡng Chất", 300000, 950000, "Tinh chất dưỡng da chuyên sâu giúp cải thiện các vấn đề về da."),
        ("Kem Dưỡng Ẩm", 150000, 750000, "Kem dưỡng ẩm cung cấp độ ẩm cần thiết giúp da luôn mịn màng."),
        ("Nước Hoa Hồng Tonic", 120000, 480000, "Nước cân bằng pH và làm sạch nhẹ nhàng sau khi rửa mặt.")
    ],
    "Makeup": [
        ("Son Kem Lì", 120000, 450000, "Son kem lì mềm mịn, lâu trôi và lên màu chuẩn."),
        ("Kem Nền Liquid Foundation", 200000, 700000, "Kem nền che khuyết điểm hoàn hảo, mỏng nhẹ tự nhiên."),
        ("Phấn Phủ Dạng Bột", 150000, 550000, "Phấn phủ kiềm dầu hiệu quả, giữ lớp trang điểm lâu trôi."),
        ("Mascara Dài Mi", 100000, 350000, "Mascara làm dày và dài mi, chống trôi nước."),
        ("Kẻ Mắt Nước Eyeliner", 90000, 300000, "Bút kẻ mắt nước sắc mảnh, dễ vẽ cho đôi mắt cuốn hút."),
        ("Phấn Má Hồng Blush", 120000, 400000, "Phấn má hồng mang lại đôi má ửng hồng tự nhiên.")
    ],
    "Personal Care": [
        ("Dầu Gội Mượt Tóc", 80000, 300000, "Dầu gội sạch gàu, nuôi dưỡng tóc mềm mượt tự nhiên."),
        ("Dầu Xả Phục Hồi", 90000, 320000, "Dầu xả phục hồi tóc hư tổn từ sâu bên trong."),
        ("Sữa Tắm Dưỡng Ẩm", 70000, 250000, "Sữa tắm làm sạch cơ thể và bổ sung dưỡng chất dưỡng ẩm."),
        ("Kem Đánh Răng", 30000, 150000, "Kem đánh răng giúp răng trắng sáng và hơi thở thơm mát."),
        ("Nước Súc Miệng", 50000, 180000, "Nước súc miệng diệt khuẩn, bảo vệ nướu vượt trội."),
        ("Lăn Khử Mùi", 40000, 120000, "Lăn khử mùi giữ vùng dưới cánh tay khô thoáng suốt 48h.")
    ],
    "Health & Wellness": [
        ("Viên Uống Dầu Cá Fish Oil", 250000, 800000, "Bổ sung Omega-3 hỗ trợ sức khỏe tim mạch và trí não."),
        ("Viên Uống Vitamin C", 150000, 500000, "Tăng cường hệ miễn dịch và dưỡng sáng da từ bên trong."),
        ("Bao Cao Su", 50000, 250000, "Sản phẩm hỗ trợ tình dục an toàn và thăng hoa."),
        ("Miếng Dán Giảm Đau", 20000, 100000, "Miếng dán giảm nhanh các cơn đau cơ và xương khớp."),
        ("Kẹo Ngậm Đau Họng", 15000, 60000, "Làm dịu cổ họng, giảm ho và ngứa rát tức thì."),
        ("Viên Uống Sáng Da Collagen", 400000, 1200000, "Bổ sung collagen giúp chống lão hóa và săn chắc da.")
    ]
}

VOLUMES = ["50ml", "100ml", "150ml", "200ml", "500ml", "30g", "50g", "100g", "30 viên", "60 viên", "120 viên", "Hộp 3 cái", "Hộp 10 cái"]

# Unsplash premium search queries for product placeholders
IMAGE_KEYWORDS = {
    "Skincare": [
        "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1608248597481-496100c8c836?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1601049541289-9b1b7bbbfe19?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=500&auto=format&fit=crop&q=60"
    ],
    "Makeup": [
        "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1625093742435-6fa192b6fb10?w=500&auto=format&fit=crop&q=60"
    ],
    "Personal Care": [
        "https://images.unsplash.com/photo-1607006342411-9a90fb38ba796?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1616683693504-3ea7e9ad6fec?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500&auto=format&fit=crop&q=60"
    ],
    "Health & Wellness": [
        "https://images.unsplash.com/photo-1584017911766-d451b3d0e843?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1611926653458-09294b3142bf?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1550572017-edd951b55104?w=500&auto=format&fit=crop&q=60",
        "https://images.unsplash.com/photo-1471864190281-a93a3070b6de?w=500&auto=format&fit=crop&q=60"
    ]
}

def generate_random_barcode():
    # EAN-13 starts with 893 for Vietnam
    prefix = "893"
    body = "".join(str(random.randint(0, 9)) for _ in range(9))
    # Calculate checksum digit
    code = prefix + body
    checksum = 0
    for i, char in enumerate(code):
        digit = int(char)
        if i % 2 == 0:
            checksum += digit
        else:
            checksum += digit * 3
    check_digit = (10 - (checksum % 10)) % 10
    return code + str(check_digit)

def create_mock_data():
    """Generates 200 items of mock SKU Master data and matching Competitor price lists"""
    # Create directories if they do not exist
    os.makedirs("data", exist_ok=True)
    
    sku_master = []
    competitor_prices = []
    
    random.seed(42)  # Seed for deterministic generation
    
    # 1. Generate 200 Products
    barcodes_seen = set()
    total_items = 200
    
    categories = list(BRANDS.keys())
    
    for i in range(total_items):
        category = random.choice(categories)
        brand = random.choice(BRANDS[category])
        prod_type, min_p, max_p, desc_tpl = random.choice(PRODUCT_TYPES[category])
        vol = random.choice(VOLUMES)
        
        # Assemble product details
        name = f"{prod_type} {brand} {vol}"
        barcode = generate_random_barcode()
        while barcode in barcodes_seen:
            barcode = generate_random_barcode()
        barcodes_seen.add(barcode)
        
        # Guardian price
        guardian_price = round(random.randint(min_p, max_p), -3) # round to thousands
        
        # Cost price (usually 60% of Guardian price to allow margins)
        cost_price = round(guardian_price * 0.60, -3)

        # Image
        image_url = random.choice(IMAGE_KEYWORDS[category])
        description = f"{desc_tpl} Hàng chính hãng phân phối tại Guardian Việt Nam."
        
        sku_master.append({
            "id": i + 1,
            "barcode": barcode,
            "name": name,
            "category": category,
            "guardian_price": guardian_price,
            "cost_price": cost_price,
            "image_url": image_url,
            "description": description
        })
        
        # 2. Generate Competitor prices (for each competitor, for past 7 days to simulate price history)
        competitors = ["Shopee", "Lazada", "TikTok Shop", "GrabMart", "Pharmacity"]
        
        # We simulate runs for 7 days
        for day_offset in range(6, -1, -1):
            scraped_date = datetime.utcnow() - timedelta(days=day_offset)
            
            for competitor in competitors:
                # Add pricing factor
                if competitor == "Shopee":
                    price_factor = random.uniform(0.83, 0.99)
                    discount_pct = random.choice([0.0, 0.05, 0.10, 0.15])
                    voucher = random.choice([None, "Mã giảm 10k", "Freeship Extra"])
                    promo = random.choice([None, "Flash Sale"])
                elif competitor == "Lazada":
                    price_factor = random.uniform(0.86, 0.98)
                    discount_pct = random.choice([0.0, 0.05, 0.10])
                    voucher = random.choice([None, "Voucher tích lũy"])
                    promo = random.choice([None, "Combo mua 2 giảm 5%"])
                elif competitor == "TikTok Shop":
                    price_factor = random.uniform(0.80, 0.96)
                    discount_pct = random.choice([0.0, 0.10, 0.15])
                    voucher = random.choice([None, "Voucher Livestream 20k"])
                    promo = random.choice([None, "Flash Sale hàng hiệu"])
                elif competitor == "GrabMart":
                    price_factor = random.uniform(0.99, 1.15)
                    discount_pct = 0.0
                    voucher = None
                    promo = None
                else: # Pharmacity
                    price_factor = random.uniform(0.96, 1.03)
                    discount_pct = random.choice([0.0, 0.05])
                    voucher = None
                    promo = None
                
                # 10% chance of competitor being OUT_OF_STOCK
                is_oos = random.random() < 0.10
                
                if is_oos:
                    raw_price = None
                    discount_amount = 0.0
                    net_price = None
                    stock_status = "OUT_OF_STOCK"
                    voucher = None
                    promo = None
                else:
                    # Base price calculation
                    raw_price = round(guardian_price * price_factor, -3)
                    discount_amount = round(raw_price * discount_pct, -3)
                    net_price = raw_price - discount_amount
                    
                    # Voucher deduction
                    if voucher and "10k" in voucher:
                        net_price = max(1000, net_price - 10000)
                    elif voucher and "20k" in voucher:
                        net_price = max(1000, net_price - 20000)
                    stock_status = "IN_STOCK"
                    
                comp_slug = competitor.lower().replace(" ", "")
                url = f"https://www.{comp_slug}.vn/search?q={barcode}"
                
                competitor_prices.append({
                    "product_id": i + 1,
                    "competitor_name": competitor,
                    "raw_price": raw_price,
                    "discount": discount_amount,
                    "net_price": net_price,
                    "stock_status": stock_status,
                    "voucher_details": voucher,
                    "promo_mechanics": promo,
                    "url": url,
                    "scraped_at": scraped_date.strftime("%Y-%m-%d %H:%M:%S")
                })
                
    # 3. Write to CSV files
    with open("data/sku_master.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "barcode", "name", "category", "guardian_price", "cost_price", "image_url", "description"])
        writer.writeheader()
        writer.writerows(sku_master)
        
    with open("data/competitor_mock.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["product_id", "competitor_name", "raw_price", "discount", "net_price", "stock_status", "voucher_details", "promo_mechanics", "url", "scraped_at"])
        writer.writeheader()
        writer.writerows(competitor_prices)
        
    print(f"Successfully generated 200 products in data/sku_master.csv")
    print(f"Successfully generated competitor mock prices in data/competitor_mock.csv")
    
    return sku_master, competitor_prices

def seed_database(sku_master, competitor_prices):
    """Seeds the local SQLite/PostgreSQL database with the generated mock data"""
    from app.db.session import SessionLocal, engine, Base
    from app.db import models
    from app.services.cpi_calculator import calculate_cpi_for_product
    
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(models.Product).count() > 0:
            print("Database already contains data. Clearing existing records for clean seeding...")
            db.query(models.Alert).delete()
            db.query(models.PricingIndex).delete()
            db.query(models.CompetitorPrice).delete()
            db.query(models.Product).delete()
            db.commit()
            
        print("Inserting product master records...")
        db_products = []
        for p in sku_master:
            db_prod = models.Product(
                id=p["id"],
                barcode=p["barcode"],
                name=p["name"],
                category=p["category"],
                guardian_price=p["guardian_price"],
                cost_price=p["cost_price"],
                image_url=p["image_url"],
                description=p["description"]
            )
            db.add(db_prod)
            db_products.append(db_prod)
        db.commit()
        
        print("Inserting competitor price history...")
        # To avoid committing too many records, insert in chunks
        chunk_size = 500
        for i in range(0, len(competitor_prices), chunk_size):
            chunk = competitor_prices[i:i+chunk_size]
            for cp in chunk:
                db_cp = models.CompetitorPrice(
                    product_id=cp["product_id"],
                    competitor_name=cp["competitor_name"],
                    raw_price=cp["raw_price"],
                    discount=cp["discount"],
                    net_price=cp["net_price"],
                    stock_status=cp.get("stock_status", "IN_STOCK"),
                    voucher_details=cp["voucher_details"],
                    promo_mechanics=cp["promo_mechanics"],
                    url=cp["url"],
                    scraped_at=datetime.strptime(cp["scraped_at"], "%Y-%m-%d %H:%M:%S")
                )
                db.add(db_cp)
            db.commit()
            print(f"  Inserted {min(i+chunk_size, len(competitor_prices))}/{len(competitor_prices)} competitor prices...")

        print("Calculating initial Competitor Pricing Indices (CPI) and generating alerts...")
        for db_prod in db_products:
            calculate_cpi_for_product(db, db_prod.id)
            
        print("Database successfully seeded and pricing calculations completed!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and seed mock data for the Guardian Pricing Platform.")
    parser.add_argument("--db", action="store_true", help="Seed the generated data directly into the database.")
    args = parser.parse_args()
    
    sku, competitor = create_mock_data()
    
    if args.db:
        seed_database(sku, competitor)
