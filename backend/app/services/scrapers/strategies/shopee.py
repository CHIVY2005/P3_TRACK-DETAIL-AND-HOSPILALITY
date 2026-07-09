# backend/app/services/scrapers/strategies/shopee.py
from typing import Dict, Any
from app.services.scrapers.base import BaseScraper

class ShopeeScraper(BaseScraper):
    async def fetch_raw_json(self, target_url: str) -> Dict[str, Any]:
        # Implement actual fetching logic via Apify or requests here
        return {}

    def clean_data(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_payload or not isinstance(raw_payload, list) or len(raw_payload) == 0:
            return {}
            
        item = raw_payload[0] 
        
        current_price = item.get("price")
        original_price = item.get("price_before_discount")
        discount_pct = item.get("discount_pct")
        promotion = f"Giảm {discount_pct}%" if discount_pct else None
        
        breadcrumbs = item.get("breadcrumb", [])
        hierarchy = " > ".join([b.get("name") for b in breadcrumbs]) if breadcrumbs else None
        
        if breadcrumbs:
            url = breadcrumbs[-1].get("url")
        else:
            url = f"https://shopee.vn/product/{item.get('shop_id')}/{item.get('item_id')}"
            
        return {
            "platform": "Shopee",
            "title": item.get("title"),
            "current_price": current_price,
            "original_price": original_price,
            "promotion": promotion,
            "sku_platform": str(item.get("item_id")),
            "hierarchy": hierarchy,
            "url": url,
            "stock_status": item.get("availability"),
            "rating": item.get("rating_star"),
            "raw_data": raw_payload
        }
