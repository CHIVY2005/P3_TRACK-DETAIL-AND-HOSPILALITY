import os
import random
import asyncio
from datetime import datetime
from typing import Callable, Optional
from sqlalchemy.orm import Session
from app.db import models
from app.config import settings
from app.services.cpi_calculator import calculate_cpi_for_product
from app.services.link_discovery import ensure_competitor_link
from app.services.platform_mappers import map_marketplace_result

# List of competitor channels
COMPETITORS = ["Shopee", "Lazada", "TikTok Shop", "GrabMart", "Pharmacity", "Hasaki"]

async def scrape_via_apify(search_target: str, competitor_name: str) -> dict:
    """
    Integrates Apify API using the user's Apify platform credits.
    Triggers a marketplace search actor on Shopee or Lazada to find live pricing.
    """
    token = os.getenv("APIFY_API_TOKEN", "")
    if not token or "your_apify" in token:
        # No key available, return None to trigger fallback
        return None

    try:
        from apify_client import ApifyClient
        client = ApifyClient(token)
        
        # Select actor based on channel
        actor_id = "apify/shopee-scraper" if competitor_name == "Shopee" else "apify/lazada-scraper"
        
        # Configure search payload
        run_input = {
            "search": search_target,
            "maxItems": 1,
            "proxy": {
                "useApifyProxy": True
            }
        }
        
        # Run the actor in a thread to keep async simple
        # (In a real production app, you would run this asynchronously via webhooks)
        run = client.actor(actor_id).call(run_input=run_input, timeout_secs=60)
        
        # Fetch results
        results = list(client.dataset(run["defaultDatasetId"]).list_items().items)
        if results:
            item = results[0]
            # Parse Shopee/Lazada raw vs net pricing fields
            raw_price = float(item.get("price_before_discount", 0) or item.get("price", 0))
            net_price = float(item.get("price", 0))
            discount = raw_price - net_price
            voucher = item.get("voucher_info", None)
            promo = item.get("promotion_name", None)
            url = item.get("url", f"https://www.shopee.vn/product/{item.get('shopid')}/{item.get('itemid')}")
            
            return {
                "raw_price": raw_price,
                "price": net_price,
                "discount": discount,
                "voucher_details": voucher,
                "promo_mechanics": promo,
                "url": url
            }
    except Exception as e:
        print(f"Apify scrape failed for {competitor_name}: {e}")
        
    return None

async def scrape_via_crawl4ai(barcode: str, competitor_name: str, target_url: str | None = None) -> dict:
    """
    Integrates Crawl4AI to crawl competitor pharmacy/health websites (e.g. Hasaki, Pharmacity)
    and parse HTML into structured price grids using markdown extraction.
    """
    if competitor_name not in ["Pharmacity", "GrabMart"]:
        return None
        
    try:
        from crawl4ai import AsyncWebCrawler
        from bs4 import BeautifulSoup
        
        # Build search URL
        search_url = ""
        if target_url:
            search_url = target_url
        elif competitor_name == "Pharmacity":
            search_url = f"https://www.pharmacity.vn/tim-kiem?q={barcode}"
        else: # GrabMart search simulation
            search_url = f"https://grab.com/mart/search?q={barcode}"
            
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=search_url, bypass_cache=True)
            
            if result.success and result.markdown:
                # Use BeautifulSoup or simple markdown keyword extraction to find prices
                # In a real setup, you'd feed this markdown to a LLM extraction schema.
                # Here we do regex/keyword fallback on the markdown content.
                import re
                prices = re.findall(r'\b\d{1,3}(?:\.\d{3})*(?:\s*₫|\s*VND)\b', result.markdown)
                if prices:
                    # Clean price string to float
                    net_str = prices[0].replace("₫", "").replace("VND", "").replace(".", "").strip()
                    net_price = float(net_str)
                    
                    return {
                        "raw_price": net_price,
                        "net_price": net_price,
                        "discount": 0.0,
                        "voucher_details": None,
                        "promo_mechanics": "Crawl4AI extracted",
                        "url": search_url
                    }
    except Exception as e:
        print(f"Crawl4AI failed for {competitor_name}: {e}")
        
    return None

async def scrape_via_playwright(barcode: str, competitor_name: str, target_url: str | None = None) -> dict:
    """
    Direct Playwright scraper for Hasaki and TikTok Shop.
    Launches a headless browser, waits for JS rendering (networkidle),
    and extracts structured price data.
    """
    if competitor_name not in ["Hasaki", "TikTok Shop"]:
        return None

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        print(f"Playwright is unavailable for {competitor_name}: {e}")
        return None

    import re
    
    url = ""
    if target_url:
        url = target_url
    elif competitor_name == "Hasaki":
        url = f"https://hasaki.vn/catalogsearch/result/?q={barcode}"
    elif competitor_name == "TikTok Shop":
        url = f"https://www.tiktok.com/search?q={barcode}"
        
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Go to page and wait for JS to load
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            price_element = None
            raw_price = None
            
            if competitor_name == "Hasaki":
                selectors = [".price_now", ".item_price", ".product-price", ".price"]
                for sel in selectors:
                    try:
                        price_element = await page.query_selector(sel)
                        if price_element:
                            price_text = await price_element.inner_text()
                            digits = re.sub(r"\D", "", price_text)
                            if digits:
                                raw_price = float(digits)
                                break
                    except Exception:
                        continue
            elif competitor_name == "TikTok Shop":
                selectors = ["div[class*='Price']", "span[class*='Price']", ".price-text"]
                for sel in selectors:
                    try:
                        price_element = await page.query_selector(sel)
                        if price_element:
                            price_text = await price_element.inner_text()
                            digits = re.sub(r"\D", "", price_text)
                            if digits:
                                raw_price = float(digits)
                                break
                    except Exception:
                        continue
                        
            await browser.close()
            
            if raw_price:
                return {
                    "raw_price": raw_price,
                    "net_price": raw_price,
                    "discount": 0.0,
                    "stock_status": "IN_STOCK",
                    "voucher_details": None,
                    "promo_mechanics": "Playwright Scraped",
                    "url": url
                }
    except Exception as e:
        print(f"Playwright scraping failed for {competitor_name}: {str(e)}")
        
    return None

def simulate_competitor_price(product_guardian_price: float, competitor_name: str, barcode: str, fallback_url: str | None = None) -> dict:
    """
    Fallback simulator pricing logic (runs if API keys are not provided).
    Simulates realistic price discrepancies, vouchers, and promos.
    """
    daily_seed = f"{datetime.utcnow().date().isoformat()}:{barcode}:{competitor_name}"
    rng = random.Random(daily_seed)

    if competitor_name == "Shopee":
        price_factor = rng.uniform(0.82, 0.98)
        discount_pct = rng.choice([0.0, 0.05, 0.10, 0.15])
        voucher = rng.choice([None, "Mã giảm 10k", "Mã giảm 20k", "Freeship Extra"])
        promo = rng.choice([None, "Mua kèm deal sốc", "Flash Sale"])
    elif competitor_name == "Lazada":
        price_factor = rng.uniform(0.85, 0.97)
        discount_pct = rng.choice([0.0, 0.05, 0.08, 0.12])
        voucher = rng.choice([None, "Voucher tích lũy", "Mã giảm 15k"])
        promo = rng.choice([None, "Combo mua 2 giảm 5%", "Flash Sale"])
    elif competitor_name == "TikTok Shop":
        price_factor = rng.uniform(0.78, 0.95)
        discount_pct = rng.choice([0.0, 0.10, 0.20])
        voucher = rng.choice([None, "Voucher Livestream 25k", "Mã người mới"])
        promo = rng.choice([None, "Flash Sale hàng hiệu"])
    elif competitor_name == "GrabMart":
        price_factor = rng.uniform(0.98, 1.15)
        discount_pct = 0.0
        voucher = None
        promo = None
    else:  # Pharmacity / website competitor
        price_factor = rng.uniform(0.95, 1.05)
        discount_pct = rng.choice([0.0, 0.05])
        voucher = None
        promo = None

    raw_price = round(product_guardian_price * price_factor, -3)
    discount_amount = round(raw_price * discount_pct, -3)
    net_price = raw_price - discount_amount
    
    voucher_val = 0
    if voucher:
        if "10k" in voucher: voucher_val = 10000
        elif "15k" in voucher: voucher_val = 15000
        elif "20k" in voucher: voucher_val = 20000
        elif "25k" in voucher: voucher_val = 25000
        net_price = max(1000, net_price - voucher_val)

    comp_slug = competitor_name.lower().replace(" ", "")
    url = fallback_url or f"https://www.{comp_slug}.vn/search?q={barcode}"

    return {
        "raw_price": raw_price,
        "net_price": net_price,
        "discount": discount_amount,
        "stock_status": "IN_STOCK",
        "voucher_details": voucher,
        "promo_mechanics": promo,
        "url": url
    }

async def scrape_competitor_prices_for_product_async(db: Session, product_id: int, force_simulation: bool = False, commit: bool = True) -> list:
    """
    Main entry point for scraping competitor prices asynchronously.
    First tries Apify (marketplaces) and Crawl4AI (web). Falls back to mock simulator if keys are missing.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return []

    new_prices = []
    
    for competitor in COMPETITORS:
        link = ensure_competitor_link(db, product, competitor, commit=commit)
        price_data = None
        
        # 1. Try real scraping only if not forced to simulate
        if not force_simulation:
            # Try real Apify integration for Shopee/Lazada
            if competitor in ["Shopee", "Lazada"]:
                price_data = await scrape_via_apify(product.name or product.barcode, competitor)
                
            # Try direct Playwright for Hasaki / TikTok Shop
            if not price_data and competitor in ["Hasaki", "TikTok Shop"]:
                price_data = await scrape_via_playwright(product.barcode, competitor, link.url if link else None)
                
            # Try Crawl4AI for independent web pages
            if not price_data and competitor in ["Pharmacity", "GrabMart"]:
                price_data = await scrape_via_crawl4ai(product.barcode, competitor, link.url if link else None)
            
        # Fallback to mock simulator if no data was fetched (or if forced to simulate)
        if not price_data:
            price_data = simulate_competitor_price(product.guardian_price, competitor, product.barcode, link.url if link else None)
        elif competitor in ["Shopee", "Lazada"]:
            price_data = map_marketplace_result(competitor, price_data, link.url if link else None)

        if link and price_data.get("url") and link.url != price_data["url"]:
            link.url = price_data["url"]
            link.discovery_method = "scraped"

        # Check for price anomalies using the historical cross-validation helper
        from app.services.cpi_calculator import check_price_anomaly
        is_suspicious = check_price_anomaly(db, product.id, competitor, price_data["net_price"])

        # Write to DB
        price_record = models.CompetitorPrice(
            product_id=product.id,
            competitor_name=competitor,
            raw_price=price_data["raw_price"],
            discount=price_data["discount"],
            net_price=price_data["net_price"],
            stock_status=price_data.get("stock_status", "IN_STOCK"),
            is_suspicious=is_suspicious,
            voucher_details=price_data["voucher_details"],
            promo_mechanics=price_data["promo_mechanics"],
            url=price_data["url"],
            scraped_at=datetime.utcnow()
        )
        db.add(price_record)
        new_prices.append(price_record)

    if commit:
        db.commit()
    else:
        db.flush()
    
    # Recalculate CPI index
    calculate_cpi_for_product(db, product.id, commit=commit)
    
    return new_prices

def scrape_realtime_competitor_prices(db: Session, product_id: int, force_simulation: bool = False, commit: bool = True) -> list:
    """
    Synchronous wrapper to run async scraper in FastAPI routes.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # Run in thread or task if loop is already running
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id, force_simulation, commit))
    else:
        return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id, force_simulation, commit))

def run_scraper_for_all_products(
    db: Session,
    progress_callback: Optional[Callable[[models.Product, int, int, str], None]] = None,
):
    # Force simulation on bulk run unless explicitly enabled in environment variables
    # to avoid launching 400 Chromium instances / blocking the server
    force_sim = os.getenv("ENABLE_REAL_SCRAPING") != "True"
    products = db.query(models.Product).all()
    results = {}
    total = len(products)
    for index, p in enumerate(products, start=1):
        if progress_callback:
            progress_callback(p, index, total, "started")
        results[p.id] = scrape_realtime_competitor_prices(db, p.id, force_simulation=force_sim, commit=False)
        if progress_callback:
            progress_callback(p, index, total, "completed")
    db.commit()
    return results
