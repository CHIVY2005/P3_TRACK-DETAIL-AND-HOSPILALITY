# Guardian Pricing — Omnichannel Scraping Pipeline

## What Was Built

### 1. CompetitorPriceDTO — [base.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/base.py)

Pydantic contract DTO with **8 mandatory fields**:

| Field | Type | Purpose |
|---|---|---|
| `barcode` | `str` | Links to `sku_master` PK |
| `platform` | `str` | Lowercase platform name |
| `product_name` | `str` | Name scraped from competitor |
| `shop_name` | `str` | Seller name (defaults to platform for Hasaki/Pharmacity) |
| `competitor_price` | `int` | Clean VND integer |
| `is_in_stock` | `bool` | Stock status |
| `promotion_info` | `Optional[str]` | Discount/gift info |
| `raw_payload` | `dict` | Full raw JSON → JSONB in Postgres |

Plus `clean_price_string()` utility — handles:
- `"413.000 ₫"` → `413000` ✓
- `"501.500 ₫/Chai"` → `501500` ✓
- `"1.250.000đ"` → `1250000` ✓
- Integer passthrough → ✓
- `"Liên hệ"` → `None` ✓

---

### 2. Platform Parsers (6 Strategies)

| File | Platform | Key Logic |
|---|---|---|
| [hasaki.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/hasaki.py) | Hasaki | `title` → name, regex clean `"413.000 ₫"`, shop = `"Hasaki"` |
| [pharmacity.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/pharmacity.py) | Pharmacity | Name from `hierarchy[-1]` or URL slug, regex strip `"₫/Chai"`, shop = `"Pharmacity"` |
| [shopee.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/shopee.py) | Shopee | Price ÷ 100,000 for Shopee internal format, `shop_name` for Mall filtering |
| [lazada.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/lazada.py) | Lazada | Plain VND, `sellerName` extraction |
| [tiktok.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/tiktok.py) | TikTok Shop | Standard Apify shape handling |
| [grabmart.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/strategies/grabmart.py) | GrabMart | `merchant_name` extraction |

---

### 3. Factory Pattern — [factory.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scrapers/factory.py)

```python
ScraperFactory.get_scraper("hasaki")  # → HasakiScraper()
ScraperFactory.get_scraper("shopee")  # → ShopeeScraper()
# ... all 6 platforms + dynamic registration
```

**Provider Swap Ready**: Override `fetch_raw_json()` to swap Apify → BrightData/ZenRows without touching parsers.

---

### 4. Async Bulk Sync — [sync.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/sync.py)

| Endpoint | Method | Response |
|---|---|---|
| `/api/sync-price/{barcode}` | POST | Sync — single product |
| `/api/v1/sync/all` | POST | **HTTP 202** — BackgroundTasks bulk |
| `/api/v1/sync/force` | POST | **HTTP 202** — Force re-scrape all |

Pipeline: `Apify raw → ScraperFactory.parse_to_dto → upsert_dtos_to_db → price_history`

Batches of 10 SKUs with `asyncio.gather()` + polite delay.

---

### 5. DB Model Extension — [models.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/db/models.py)

`PriceHistory` now includes:
- `product_name` (String) — scraped product name
- `shop_name` (String) — seller name
- `is_in_stock` (Boolean) — stock status

---

### 6. Config — [config.py](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/config.py)

Added `APIFY_ACTOR_{SHOPEE,LAZADA,TIKTOK,GRABMART,HASAKI,PHARMACITY}` + `SCRAPER_PROVIDER` toggle + `get_actor_id_for_platform()` resolver.

---

### 7. Fallback Fixture — [apify_fallback_fixture.json](file:///f:/JOB/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/data/apify_fallback_fixture.json)

10 mock items covering all 5 barcodes × 6 platforms with `product_name`, `shop_name`, realistic VND prices (string & int formats), and promotions.

## Verification Results

```
✓ CompetitorPriceDTO serialization works
✓ clean_price_string handles all Vietnamese price formats
✓ HasakiParser: "413.000 ₫" → 413000
✓ PharmacityParser: "501.500 ₫/Chai" → 501500, name from hierarchy
✓ ShopeeParser: 66900000000 ÷ 100k → 669000
✓ ScraperFactory resolves all 7 platform keys → 6 scraper classes
✓ sync.py imports clean with 3 route endpoints
```
