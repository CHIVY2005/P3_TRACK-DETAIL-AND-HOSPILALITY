from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
import urllib.parse

from app.database import get_db
from app.models import SkuMaster, CompetitorLink, PriceHistory
from app.services.ai_matcher import generate_embeddings
from app.services.apify_client import ApifyClientService

router = APIRouter()
apify_service = ApifyClientService()

class SyncResponse(BaseModel):
    status: str
    matched_product: Optional[Dict[str, Any]] = None
    updated_price: Optional[float] = None
    message: Optional[str] = None

@router.post("/sync-price/{barcode}", response_model=SyncResponse)
def sync_price(barcode: str, platform: str = "Hasaki", db: Session = Depends(get_db)):
    # 1. Query DB: Fetch the product from sku_master using the barcode.
    sku = db.query(SkuMaster).filter(SkuMaster.barcode == barcode).first()
    if not sku:
        raise HTTPException(status_code=404, detail="Product not found in SkuMaster")
        
    # 2. Check Existing Link: Query competitor_links for a specific platform.
    existing_link = db.query(CompetitorLink).filter(
        CompetitorLink.barcode == barcode,
        CompetitorLink.platform == platform
    ).first()
    
    match = None
    
    if existing_link:
        # If link exists: Call ApifyClientService with this direct URL to get the price.
        try:
            # We assume a wrapper or the exact signature exists. Passing actor_id as dummy for Hasaki.
            results = apify_service.run_scraper(actor_id="hasaki-scraper-actor-id", target_url=existing_link.url)
            if results and isinstance(results, list):
                match = results[0]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")
    else:
        # If link DOES NOT exist (Fallback to AI Search):
        # a. Construct a search URL based on the product name
        url_encoded_name = urllib.parse.quote_plus(sku.product_name)
        search_url = f"https://hasaki.vn/tim-kiem?q={url_encoded_name}"
        
        # b. Call ApifyClientService to scrape the Top 5 results from this search page
        try:
            results = apify_service.run_scraper(actor_id="hasaki-search-actor-id", target_url=search_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")
            
        if not results:
            return {"status": "not_found", "message": "No results found from search"}
            
        top_5_results = results[:5]
        
        # 3. AI Vector Matching
        titles = [item.get("title", "") for item in top_5_results]
        embeddings = generate_embeddings(titles)
        
        best_match = None
        best_score = -1.0
        
        for idx, emb in enumerate(embeddings):
            # Compare embedding against the sku_master.name_embedding using pgvector
            # 1 - cosine_distance gives the cosine similarity
            similarity_query = select(1 - SkuMaster.name_embedding.cosine_distance(emb)).where(
                SkuMaster.barcode == barcode
            )
            score = db.scalar(similarity_query)
            
            if score is not None and score > best_score:
                best_score = score
                best_match = top_5_results[idx]
        
        # If the similarity score is above a threshold (e.g., > 0.85)
        if best_score > 0.85 and best_match:
            match = best_match
            
            # Persist Data: Insert the matched url into the competitor_links table
            new_link = CompetitorLink(
                barcode=barcode,
                platform=platform,
                url=match.get("url"),
                platform_item_id=None
            )
            db.add(new_link)
            db.commit()

    if match:
        price = match.get("price")
        if price is not None:
            # Ensure price is integer as per PriceHistory model
            scraped_price_int = int(float(price))
            
            # Persist Data: Insert the parsed price into the price_history table.
            new_price = PriceHistory(
                barcode=barcode,
                platform=platform,
                scraped_price=scraped_price_int,
                promotion=match.get("promotion", None)
            )
            db.add(new_price)
            db.commit()
            
            return {
                "status": "success",
                "matched_product": match,
                "updated_price": price
            }
        else:
            return {"status": "error", "message": "Matched product does not contain a price."}
    else:
        return {"status": "not_found", "message": "No valid match found."}
