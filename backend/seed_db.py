import sys
import os

# Avoid Windows console encoding crashes when seeded product names contain
# Vietnamese characters.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="backslashreplace")

# Ensure the backend directory is in the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.db.models import Base, SkuMaster, CompetitorLink

from sqlalchemy import text

def seed():
    # 1. Automatically create all tables defined in our SQLAlchemy models
    print("Ensuring pgvector extension is installed...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not create vector extension automatically: {e}")

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    # Data to Insert
    products_data = [
        {
            "barcode": "8931111111111",
            "name": "La Roche-Posay Anthelios XL SPF50+ PA++++ 50ml",
            "category": "Skincare",
            "guardian_price": 450000,
            "competitor_platform": "Shopee",
            "competitor_url": "https://shopee.vn/-PHI%C3%8AN-B%E1%BA%A2N-N%C3%82NG-TONE-Kem-ch%E1%BB%91ng-n%E1%BA%AFng-n%C3%A2ng-tone-cho-da-d%E1%BA%A7u-La-Roche-Posay-Anthelios-XL-SPF50-PA-50ml-i.37251700.580590480"
        },
        {
            "barcode": "8932222222222",
            "name": "Simple Purifying Gel Wash 150ml",
            "category": "Skincare",
            "guardian_price": 150000,
            "competitor_platform": "Shopee",
            "competitor_url": "https://shopee.vn/S%E1%BB%AFa-R%E1%BB%ADa-M%E1%BA%B7t-Ki%E1%BB%81m-D%E1%BA%A7u-H%E1%BB%97-Tr%E1%BB%A3-Gi%E1%BA%A3m-M%E1%BB%A5n-Simple-Purifying-Gel-Wash-150ml-i.412741369.23828622048"
        },
        {
            "barcode": "8933333333333",
            "name": "Sáp Dưỡng Ẩm Vaseline 50ml",
            "category": "Skincare",
            "guardian_price": 80000,
            "competitor_platform": "Shopee",
            "competitor_url": "https://shopee.vn/S%C3%A1p-D%C6%B0%E1%BB%A1ng-%E1%BA%A8m-Vaseline-50ml-i.152872415.6047417280"
        }
    ]

    # Open a session
    db = SessionLocal()
    
    try:
        print("Seeding data...")
        for p_data in products_data:
            # Check if the data already exists to avoid duplicate key errors
            existing_sku = db.query(SkuMaster).filter(SkuMaster.barcode == p_data["barcode"]).first()
            
            if not existing_sku:
                # Create SkuMaster record
                new_sku = SkuMaster(
                    barcode=p_data["barcode"],
                    product_name=p_data["name"],
                    category=p_data["category"],
                    guardian_price=p_data["guardian_price"],
                    # Crucial detail: array of 384 zeros as a placeholder for pgvector
                    name_embedding=[0.0] * 384
                )
                db.add(new_sku)
                db.flush() # Flush to ensure the SKU is created before adding relationships
                
                # Create CompetitorLink record
                new_link = CompetitorLink(
                    barcode=new_sku.barcode,
                    platform=p_data["competitor_platform"],
                    url=p_data["competitor_url"]
                )
                db.add(new_link)
                
                print(f"Inserted: {p_data['name']}")
            else:
                print(f"Skipped (Already exists): {p_data['name']}")

        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
