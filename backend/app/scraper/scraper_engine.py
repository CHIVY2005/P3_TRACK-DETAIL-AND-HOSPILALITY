import os
import re
import random
import asyncio
import difflib
import unicodedata
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.db import models
from app.config import settings, get_scrape_cost_for
from app.services.cpi_calculator import calculate_cpi_for_product
from app.services.link_discovery import ensure_competitor_link
from app.services.platform_mappers import map_marketplace_result

# List of competitor channels
# GrabMart is a grocery-delivery service, not a cosmetics/pharma price channel in VN, so
# it is intentionally excluded from the tracked competitor set.
COMPETITORS = ["Shopee", "Lazada", "Pharmacity", "Hasaki"]

# Real scrapers fail often on bot-protected search URLs, so keep timeouts short and
# fall back to the simulator quickly instead of blocking the pipeline for a minute.
SCRAPE_TIMEOUT_MS = 8000        # Playwright / Crawl4AI page load budget
APIFY_TIMEOUT_SECS = 60         # Apify actor run budget (abotapi Lazada ~34s, Shopee faster)
BRIGHTDATA_TIMEOUT_SECS = 55    # Bright Data Web Unlocker request budget (JS render is slow)
# Safety ceiling per run. Must sit ABOVE this actor's real ~$0.20/run charge, otherwise
# the platform aborts the run right as it finishes and the result is lost.
APIFY_MAX_CHARGE_USD = float(os.getenv("APIFY_MAX_CHARGE_USD", "0.30"))
# How many SKUs to scrape in parallel. Each SKU already fans out to several channels
# concurrently, and real scrapers (Apify/Bright Data) are slow + rate-limited, so keep
# this low or 5 SKUs x 3 channels = 15 concurrent calls overwhelm the pool and time out
# into the simulator. Tune via the SCRAPER_PRODUCT_CONCURRENCY env var.
PRODUCT_CONCURRENCY = int(os.getenv("SCRAPER_PRODUCT_CONCURRENCY", "3"))

# Real Apify actors per marketplace (Store actor id + a builder for their input schema).
# Each actor has its own input shape; the raw output item is handed to
# map_marketplace_result which already understands the common price fields.
APIFY_MARKET_COUNTRY = os.getenv("APIFY_MARKET_COUNTRY", "vn")


def _shopee_xtracto_input(search_target: str) -> dict:
    # Schema: xtracto/shopee-scraper (mode=keyword). Fetch a few candidates so the
    # matcher can skip combos/wrong sizes instead of blindly taking the first hit.
    return {
        "mode": "keyword",
        "keyword": search_target,
        "country": APIFY_MARKET_COUNTRY,
        "sort": "relevancy",
        "maxProducts": MATCH_CANDIDATES,
    }


def _lazada_abotapi_input(search_target: str) -> dict:
    # Schema: abotapi/lazada-scraper (mode=search). Faster (~34s) than fatihtahta and
    # returns flat, numeric VND fields. country supports 'vn'.
    return {
        "mode": "search",
        "country": APIFY_MARKET_COUNTRY,
        "queries": [search_target],
        "sortBy": "popularity",
    }


def _normalize_passthrough(item: dict) -> dict:
    # xtracto/shopee-scraper is already flat (name/price/original_price/url).
    return item


def _normalize_lazada_abotapi(item: dict) -> dict:
    # abotapi/lazada-scraper: flat fields, prices already numeric in VND.
    return {
        "name": item.get("productName") or item.get("name"),
        "url": item.get("productUrl") or item.get("url"),
        "price": item.get("currentPrice"),
        "original_price": item.get("originalPrice"),
        "availability": "InStock" if item.get("inStock") else "OutOfStock",
    }


# competitor -> (actor id, input builder, output normalizer to the shared price shape)
APIFY_ACTORS = {
    "Shopee": ("xtracto/shopee-scraper", _shopee_xtracto_input, _normalize_passthrough),
    "Lazada": ("abotapi/lazada-scraper", _lazada_abotapi_input, _normalize_lazada_abotapi),
    # TikTok Shop: available actors return USD prices -> unsafe for VND CPI (not wired).
}


# ---- Product matching -------------------------------------------------------------
# Scrapers search by keyword and can return combos / different sizes; pick the candidate
# that best matches the guardian product name and sits in a sane price band instead of
# blindly taking the first result (which is what triggers "Suspicious" anomaly flags).
MATCH_CANDIDATES = int(os.getenv("SCRAPER_MATCH_CANDIDATES", "6"))
_COMBO_WORDS = ("combo", "set", "pack", "gift", "bundle", "bundle", "qua tang", "tang kem", "x2", "x3", "x 2", "x 3")


def _normalize_name(text: str) -> str:
    stripped = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", stripped.lower())


def _match_score(name: str, price, product_name: str, guardian_price) -> float:
    norm_candidate = _normalize_name(name)
    norm_target = _normalize_name(product_name)
    if not norm_candidate:
        return -1.0

    ratio = difflib.SequenceMatcher(None, norm_candidate, norm_target).ratio()
    target_tokens = set(norm_target.split())
    overlap = len(target_tokens & set(norm_candidate.split())) / max(len(target_tokens), 1)
    score = 0.6 * ratio + 0.4 * overlap

    if any(word in norm_candidate for word in _COMBO_WORDS):
        score -= 0.30  # combos/gift sets distort per-unit price

    # Price sanity vs guardian price: penalize far-off prices (likely wrong item/size).
    try:
        if guardian_price and price:
            rel = float(price) / float(guardian_price)
            if rel > 2.2 or rel < 0.35:
                score -= 0.40
            elif rel > 1.6 or rel < 0.55:
                score -= 0.15
    except (TypeError, ValueError):
        pass

    return score


def _best_candidate(candidates: list, product_name: str, guardian_price) -> dict:
    """Pick the normalized candidate ({name, price, ...}) that best matches the SKU."""
    best, best_score = None, None
    for candidate in candidates:
        if not candidate or not candidate.get("price"):
            continue
        score = _match_score(candidate.get("name") or "", candidate.get("price"), product_name, guardian_price)
        if best_score is None or score > best_score:
            best, best_score = candidate, score
    return best


def apify_enabled() -> bool:
    """Real Apify calls cost money (~$0.20/SKU), so they are OFF unless explicitly
    enabled. Without this, one bulk refresh of 200 SKUs could burn ~$40 of credit."""
    return os.getenv("APIFY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


async def scrape_via_apify(search_target: str, competitor_name: str, guardian_price=None) -> dict:
    """
    Integrates Apify using the user's platform credits. Runs the configured marketplace
    actor for a keyword search and returns the best-matching candidate (mapped downstream
    by map_marketplace_result). Returns None on any miss so the pipeline falls back.
    """
    if not apify_enabled():
        return None

    token = os.getenv("APIFY_API_TOKEN", "")
    if not token or "your_apify" in token:
        return None

    actor = APIFY_ACTORS.get(competitor_name)
    if not actor:
        # No real actor wired for this marketplace yet.
        return None
    actor_id, build_input, normalize = actor

    try:
        from apify_client import ApifyClient
        client = ApifyClient(token)
        run_input = build_input(search_target)

        # Apify's client is synchronous and would block the event loop, so run it in a
        # worker thread and cap the run so a stuck actor can't stall the batch.
        # max_items + max_total_charge_usd protect against runaway credit usage.
        def _run_actor():
            run = client.actor(actor_id).call(
                run_input=run_input,
                run_timeout=timedelta(seconds=APIFY_TIMEOUT_SECS),
                max_items=MATCH_CANDIDATES,
                max_total_charge_usd=APIFY_MAX_CHARGE_USD,
            )
            # apify-client 3.x returns a typed Run object; normalize to get the dataset id.
            run_data = dict(run)
            dataset_id = run_data.get("default_dataset_id") or run_data.get("defaultDatasetId")
            return list(client.dataset(dataset_id).list_items().items)

        # Actors occasionally return empty/error for a given query; retry once.
        for attempt in range(2):
            try:
                results = await asyncio.wait_for(
                    asyncio.to_thread(_run_actor), timeout=APIFY_TIMEOUT_SECS + 10
                )
                if results:
                    # Normalize every candidate, then pick the one that best matches the
                    # guardian SKU (name + price band) instead of blindly taking the first.
                    candidates = [normalize(item) for item in results]
                    return _best_candidate(candidates, search_target, guardian_price)
            except Exception as e:
                print(f"Apify scrape failed for {competitor_name} (attempt {attempt + 1}): {e}")
    except Exception as e:
        print(f"Apify setup failed for {competitor_name}: {e}")

    return None

BRIGHTDATA_API_URL = "https://api.brightdata.com/request"
# Hasaki (Tailwind-based) renders prices via JS: the sale price is an orange bold span,
# the original price a line-through span. Bright Data must render JS (render=True).
HASAKI_VND_PATTERN = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def _parse_vnd(text: str):
    match = HASAKI_VND_PATTERN.search(text or "")
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group())
    return float(digits) if digits else None


async def scrape_via_brightdata(barcode: str, competitor_name: str, target_url: str | None = None) -> dict:
    """
    Fetch a competitor page through Bright Data's Web Unlocker API (token-based) to bypass
    bot protection, then parse the price from the returned HTML. Wired for Hasaki only.
    Returns None (-> pipeline falls back) unless BRIGHTDATA_API_TOKEN + BRIGHTDATA_ZONE are set.
    """
    if competitor_name != "Hasaki":
        return None

    token = (os.getenv("BRIGHT_DATA_KEY", "") or os.getenv("BRIGHTDATA_API_TOKEN", "")).strip()
    zone = os.getenv("BRIGHTDATA_ZONE", "").strip()
    if not token or not zone:
        return None

    # Always hit Hasaki's catalogsearch endpoint (the tim-kiem page has a different
    # layout our selectors don't match). Reuse the name-based query from the link URL.
    from urllib.parse import urlparse, parse_qs, quote
    query = barcode
    if target_url:
        parsed_q = parse_qs(urlparse(target_url).query).get("q")
        if parsed_q:
            query = parsed_q[0]
    url = f"https://hasaki.vn/catalogsearch/result/?q={quote(query)}"

    def _fetch_html():
        import requests
        resp = requests.post(
            BRIGHTDATA_API_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            # render=True runs JS so Hasaki's client-side prices are present in the HTML.
            json={"zone": zone, "url": url, "format": "raw", "render": True},
            timeout=BRIGHTDATA_TIMEOUT_SECS,
        )
        resp.raise_for_status()
        return resp.text

    from bs4 import BeautifulSoup

    # Bright Data's JS render is occasionally flaky (returns before prices render), so
    # retry once before giving up to the simulator.
    for attempt in range(2):
        try:
            html = await asyncio.wait_for(asyncio.to_thread(_fetch_html), timeout=BRIGHTDATA_TIMEOUT_SECS + 5)
            soup = BeautifulSoup(html, "html.parser")

            # Sale price = first orange bold span; original = first line-through span.
            sale_el = soup.select_one("span.text-orange.font-bold") or soup.select_one("span.text-orange")
            original_el = soup.select_one("span.line-through")
            net_price = _parse_vnd(sale_el.get_text()) if sale_el else None
            raw_price = _parse_vnd(original_el.get_text()) if original_el else None

            if net_price:
                raw_price = raw_price or net_price
                return {
                    "raw_price": raw_price,
                    "net_price": net_price,
                    "discount": max(raw_price - net_price, 0.0),
                    "stock_status": "IN_STOCK",
                    "voucher_details": None,
                    "promo_mechanics": "Bright Data",
                    "url": url,
                }
        except Exception as e:
            print(f"Bright Data scrape failed for {competitor_name} (attempt {attempt + 1}): {e}")

    return None


# Pharmacity public search API. Override via PHARMACITY_API_URL in .env; must contain a
# "{keyword}" placeholder where the URL-encoded search term is inserted.
PHARMACITY_API = os.getenv(
    "PHARMACITY_API_URL",
    "https://api-gateway.pharmacity.vn/pmc-ecm-product/api/public/search/index"
    "?platform=1&index=1&limit=5&total=0&refresh=true&order=desc&order_by=de-xuat&keyword={keyword}",
)


async def scrape_via_pharmacity_api(search_target: str, competitor_name: str, guardian_price=None) -> dict:
    """Hit Pharmacity's public search JSON API directly (free, no proxy/render needed).
    Prices live in data.items[].variants[]; pick the best-matching item."""
    if competitor_name != "Pharmacity":
        return None

    from urllib.parse import quote

    url = PHARMACITY_API.format(keyword=quote(search_target))

    def _fetch_json():
        import requests
        resp = requests.get(url, headers={"User-Agent": settings.USER_AGENT}, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    try:
        data = await asyncio.wait_for(asyncio.to_thread(_fetch_json), timeout=settings.REQUEST_TIMEOUT + 5)
        items = ((data or {}).get("data") or {}).get("items") or []

        candidates = []
        for item in items:
            variants = item.get("variants") or []
            if not variants or not variants[0].get("price"):
                continue
            variant = variants[0]
            raw_price = variant.get("original_price") or variant.get("price")
            stock = "IN_STOCK" if (variant.get("stock_status") or "").upper() == "AVAILABLE" else "OUT_OF_STOCK"
            candidates.append({
                "name": item.get("name"),
                "raw_price": float(raw_price),
                "net_price": float(variant["price"]),
                "price": float(variant["price"]),  # used by the matcher
                "discount": max(float(raw_price) - float(variant["price"]), 0.0),
                "stock_status": stock,
                "voucher_details": None,
                "promo_mechanics": "Pharmacity API",
                "url": f"https://www.pharmacity.vn/{item.get('slug', '')}",
            })

        return _best_candidate(candidates, search_target, guardian_price)
    except Exception as e:
        print(f"Pharmacity API failed: {e}")

    return None


async def scrape_via_crawl4ai(barcode: str, competitor_name: str, target_url: str | None = None) -> dict:
    """
    Integrates Crawl4AI to crawl competitor pharmacy/health websites (e.g. Hasaki, Pharmacity)
    and parse HTML into structured price grids using markdown extraction.
    """
    if competitor_name not in ["Pharmacity"]:
        return None

    try:
        from crawl4ai import AsyncWebCrawler
        from bs4 import BeautifulSoup

        # Build search URL
        search_url = target_url or f"https://www.pharmacity.vn/tim-kiem?q={barcode}"

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=search_url, bypass_cache=True, page_timeout=SCRAPE_TIMEOUT_MS)
            
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
    if competitor_name not in ["Hasaki"]:
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
            await page.goto(url, wait_until="networkidle", timeout=SCRAPE_TIMEOUT_MS)
            
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

async def _fetch_competitor_price(product, competitor: str, link_url):
    """Fetch one channel's price (network only, no DB) so callers can run channels in
    parallel. Always returns a dict: a real scrape result or the simulator fallback."""
    price_data = None

    # 1. Try real Apify integration for Shopee/Lazada
    if competitor in ["Shopee", "Lazada"]:
        price_data = await scrape_via_apify(product.name or product.barcode, competitor, product.guardian_price)
        if price_data:
            price_data = map_marketplace_result(competitor, price_data, link_url)

    # 2a. Try Bright Data Web Unlocker API for Hasaki (bypasses bot protection).
    if not price_data and competitor in ["Hasaki"]:
        price_data = await scrape_via_brightdata(product.barcode, competitor, link_url)

    # 2b. Fall back to direct Playwright for Hasaki (TikTok Shop left to simulator).
    if not price_data and competitor in ["Hasaki"]:
        price_data = await scrape_via_playwright(product.barcode, competitor, link_url)

    # 3a. Pharmacity: hit its public search JSON API directly (free, reliable).
    if not price_data and competitor in ["Pharmacity"]:
        price_data = await scrape_via_pharmacity_api(product.name or product.barcode, competitor, product.guardian_price)

    # 3b. Fall back to Crawl4AI for independent web pages.
    if not price_data and competitor in ["Pharmacity"]:
        price_data = await scrape_via_crawl4ai(product.barcode, competitor, link_url)

    # 4. Fallback to the simulator so every channel always yields a comparable price
    if not price_data:
        price_data = simulate_competitor_price(product.guardian_price, competitor, product.barcode, link_url)

    return price_data


async def scrape_competitor_prices_for_product_async(db: Session, product_id: int) -> list:
    """
    Main entry point for scraping competitor prices asynchronously.
    All channels are fetched concurrently; a failed/slow real scraper falls back to the
    simulator quickly so one channel never stalls the others.
    """
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return []

    # Ensure links first (sync DB), then fetch every channel in parallel.
    links = {competitor: ensure_competitor_link(db, product, competitor) for competitor in COMPETITORS}
    fetched = await asyncio.gather(
        *(_fetch_competitor_price(product, competitor, links[competitor].url if links[competitor] else None)
          for competitor in COMPETITORS),
        return_exceptions=True,
    )

    from app.services.cpi_calculator import check_price_anomaly

    new_prices = []
    for competitor, price_data in zip(COMPETITORS, fetched):
        # A channel that raised is not fatal: fall back to the simulator.
        if isinstance(price_data, Exception) or not price_data:
            link = links[competitor]
            price_data = simulate_competitor_price(
                product.guardian_price, competitor, product.barcode, link.url if link else None
            )

        link = links[competitor]
        if link and price_data.get("url") and link.url != price_data["url"]:
            link.url = price_data["url"]
            link.discovery_method = "scraped"

        is_suspicious = check_price_anomaly(db, product.id, competitor, price_data["net_price"])

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
            scrape_cost=get_scrape_cost_for(competitor),
            scraped_at=datetime.now(timezone.utc)
        )
        db.add(price_record)
        new_prices.append(price_record)

    db.commit()

    # Recalculate CPI index
    calculate_cpi_for_product(db, product.id)

    return new_prices

def scrape_realtime_competitor_prices(db: Session, product_id: int) -> list:
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
        return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id))
    else:
        return loop.run_until_complete(scrape_competitor_prices_for_product_async(db, product_id))

async def _scrape_all_products_async(product_ids: list) -> dict:
    """Scrape many SKUs concurrently, each on its own DB session (Sessions are not safe
    to share across concurrent coroutines), bounded by PRODUCT_CONCURRENCY."""
    from concurrent.futures import ThreadPoolExecutor
    from app.db.session import SessionLocal

    # asyncio.to_thread shares a small default pool; the blocking Apify/Bright Data calls
    # would starve it and time out into the simulator, so give them plenty of workers.
    loop = asyncio.get_event_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=max(32, PRODUCT_CONCURRENCY * len(COMPETITORS))))

    semaphore = asyncio.Semaphore(PRODUCT_CONCURRENCY)

    async def _one(product_id: int):
        async with semaphore:
            worker_db = SessionLocal()
            try:
                rows = await scrape_competitor_prices_for_product_async(worker_db, product_id)
                return product_id, rows
            except Exception as exc:
                print(f"Scrape failed for product {product_id}: {exc}")
                return product_id, []
            finally:
                worker_db.close()

    pairs = await asyncio.gather(*(_one(pid) for pid in product_ids))
    return dict(pairs)


def run_scraper_for_all_products(db: Session):
    product_ids = [pid for (pid,) in db.query(models.Product.id).all()]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()

    results = loop.run_until_complete(_scrape_all_products_async(product_ids))
    return results
