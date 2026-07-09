import asyncio
import urllib.parse
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from app.db.models import SkuMaster, CompetitorLink

# Initialize model lazily/globally for performance
model = SentenceTransformer('all-MiniLM-L6-v2')

async def discover_competitor_link(sku_id: str, product_name: str, db: Session) -> str:
    try:
        # Phase 1: Vector Similarity Search
        query_vector = model.encode(product_name).tolist()
        
        # Query closest match using pgvector operator
        best_match = (
            db.query(CompetitorLink)
            .order_by(CompetitorLink.name_embedding.cosine_distance(query_vector))
            .first()
        )
        
        # Calculate raw distance if match exists
        if best_match:
            # Check contextually using standard pgvector distance binding
            distance = db.scalar(best_match.name_embedding.cosine_distance(query_vector))
            if distance is not None and distance < 0.15:
                return best_match.url

        # Phase 2: Fallback Search-Driven Trigger (If threshold fails)
        # Simulate or call Apify Shopee scraper link discovery logic
        encoded_name = urllib.parse.quote_plus(product_name)
        fallback_url = f"https://shopee.vn/search?keyword={encoded_name}"
        
        # Phase 3: Cache Write-back to competitor_links
        new_link = CompetitorLink(
            barcode=sku_id,  # Assume barcode maps to sku_id from context
            platform="Shopee",
            url=fallback_url,
            name_embedding=query_vector
        )
        db.add(new_link)
        db.commit()
        db.refresh(new_link)
        
        return fallback_url
        
    except Exception as e:
        db.rollback()
        # Fallback safeguard
        encoded_name = urllib.parse.quote_plus(product_name)
        return f"https://shopee.vn/search?keyword={encoded_name}"
