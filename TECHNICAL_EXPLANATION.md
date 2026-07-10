# TECHNICAL EXPLANATION

Tai lieu nay tap trung vao cau hoi "du lieu chay nhu the nao" va "tai sao he thong ra quyet dinh nhu vay".

## 1. Truc quan workflow tong

```text
Upload dataset
  -> Product + optional CompetitorLink
  -> link discovery neu thieu URL
  -> scraper hybrid lay gia doi thu
  -> CPI engine tinh index va tao alert
  -> agent doc alert va tao action
  -> human approve / reject
```

## 2. Workflow 1: Dynamic ingestion

Nguon vao co the la:

- `csv`
- `json`

Route:

- `POST /api/v1/products/import-dataset`

Backend flow:

1. `products.py` doc file upload
2. `data_ingestion.py` parse records
3. field aliases duoc map ve schema chung
4. `Product` duoc tao
5. neu file co URL doi thu, `CompetitorLink` duoc tao ngay
6. sau import, scraper MVP chay cho tung SKU

Ly do ton tai workflow nay:

- du lieu that tu ban to chuc co the thay doi format
- khong muon moi lan co CSV moi lai phai sua `seed_db.py`

## 3. Workflow 2: Link discovery

Van de business:

- nhieu luc chi co ten san pham, chua co link Shopee / Hasaki / Lazada

Giai phap hien tai:

1. `link_discovery.py` kiem tra `CompetitorLink`
2. neu chua co, no tao search URL theo platform
3. scraper dung search URL nay lam diem bat dau

Day chua phai semantic matching production-grade, nhung no giai quyet duoc bai toan MVP:

- co the bat dau crawl ngay
- khong can doi user bo sung URL thu cong

## 4. Workflow 3: Hybrid scraping

File trung tam:

- `backend/app/scraper/scraper_engine.py`

He thong thu lan luot:

### Shopee / Lazada

- uu tien luong marketplace
- co the map payload raw qua `platform_mappers.py`

### Hasaki / TikTok Shop

- uu tien `Playwright`

### Pharmacity / GrabMart

- uu tien `Crawl4AI`

### Fallback

Neu tat ca deu that bai:

- dung `simulate_competitor_price()`

Y nghia ky thuat:

- demo khong bi dung do anti-bot, rate-limit, firewall, hay missing key
- flow nghiep vu van chay duoc tu dau den cuoi

## 5. Workflow 4: Price normalization

Van de:

- payload crawl tu moi kenh co shape khac nhau
- co kenh co `price_before_discount`
- co kenh co `price`
- co kenh co `promotion_name`

Giai phap:

- `platform_mappers.py` quy tat ca ve mot schema noi bo:
  - `raw_price`
  - `net_price`
  - `discount`
  - `voucher_details`
  - `promo_mechanics`
  - `stock_status`
  - `url`

Day la dieu kien bat buoc de CPI engine va frontend co the doc du lieu mot cach on dinh.

## 6. Workflow 5: CPI va alert engine

File trung tam:

- `backend/app/services/cpi_calculator.py`

Cho tung product, engine:

1. lay latest price cua moi competitor
2. bo qua:
   - `OUT_OF_STOCK`
   - `net_price = None`
   - `is_suspicious = True`
3. tinh `average_competitor_price`
4. tinh:

```text
CPI = guardian_price / average_competitor_price * 100
```

5. dua ra recommendation:
   - `Lower Price`
   - `Increase Price`
   - `Maintain Price`
6. tao alert theo threshold

## 7. Workflow 6: Anomaly detection

Van de:

- scrape that co the doc nham gia
- listing doi thu co the co outlier

Giai phap:

- `check_price_anomaly()` so record moi voi lich su 10 lan scrape gan nhat
- neu lech qua 50% -> danh dau `is_suspicious = True`

Tac dung:

- dashboard va CPI engine khong tin mu quang vao du lieu raw moi nhat

## 8. Workflow 7: Agent reasoning

Agent da duoc tach thanh nhieu lop.

### 8.1 Market Observer

Nhiem vu:

- lay latest clean competitor price
- bien alert thanh decision context cho `agent/briefing`

Output cua no la object frontend doc truc tiep duoc:

- product nao co van de
- doi thu nao dang re hon
- gap gia bao nhieu
- margin neu match
- nen match hay negotiate

### 8.2 Margin Guardian

Nhiem vu:

1. tinh current margin
2. tinh margin if matched
3. doc config `min_margin`
4. ap dung rule-based decision summary co cau truc
5. ghi lai ly do de trace va de operator doc

Quyet dinh:

- `match`
- `negotiate`

### 8.3 Supplier Negotiator

Neu `match` khong an toan:

1. tra policy theo rule-based template
2. tao email draft
3. tao action `SUPPLIER_EMAIL_DRAFT`

### 8.4 Orchestrator

Nhiem vu:

1. tao `AgentTask`
2. tuy chon refresh market data
3. loop unresolved alerts
4. goi Margin Guardian
5. goi Supplier Negotiator neu can
6. persist actions va logs

## 9. Workflow 8: Human approval

Action quan trong nhat la `AUTO_PRICE_MATCH`.

Luot approve:

1. frontend goi `POST /agent/actions/{id}/approve`
2. backend mark action `Approved`
3. update `Product.guardian_price`
4. resolve cac alert lien quan

Luot reject:

1. frontend goi `POST /agent/actions/{id}/reject`
2. backend mark `Rejected`
3. resolve alert lien quan

Y nghia:

- AI co quyen de xuat
- con nguoi giu quyen thi hanh

## 10. Workflow 9: Dashboard read model

Frontend overview khong tu ghep du lieu bang tay tu nhieu endpoint nho nua.

Endpoint:

- `GET /api/v1/agent/briefing`

API nay gom:

- summary
- priority queue
- channel summary
- latest task
- pending action count

No bien backend thanh mot `read model` phuc vu rieng cho dashboard.

## 11. Workflow 10: Daily autonomous cycle

Theo brief `hybrid scheduler`, he thong hien tai da co luong chay ngam dinh ky.

Current behavior:

- scheduler start cung FastAPI app
- interval mac dinh la `86400` giay
- moi tick se:
  1. refresh market data
  2. chay agent orchestration
  3. tao action moi neu co alert hop le

Co che an toan:

- neu agent dang chay thu cong, scheduler se bo qua tick do
- runtime status co the doc qua `GET /api/v1/agent/runtime-status`

## 12. Workflow 11: Branch evidence

File:

- `dataset_shopee-scraper_*.json`

Service:

- `scraped_samples.py`

Muc dich:

- show bang chung branch crawl co data that
- match nhe listing voi catalog hien tai
- dua evidence vao man Mission Control

Day la lop adapter cho pitch, khong phai matching engine production.

## 13. Vi sao kien truc hien tai hop ly cho hackathon

No can bang duoc 3 dieu:

1. `Demoability`
   - khong phu thuoc hoan toan vao scrape that
   - co seed, fallback, approval flow

2. `Extensibility`
   - ingestion, discovery, scrape, agent duoc tach module
   - co the thay tung lop ma khong pha toan bo flow

3. `Explainability`
   - dashboard doc duoc decision context
   - agent co logs
   - Langfuse co `decision_summary`
   - action co trang thai ro rang

## 14. Gioi han ky thuat hien tai

- search-driven link discovery moi la MVP
- chua co worker queue
- chua co auth
- frontend build trong sandbox nay van vuong Vite/esbuild do issue parent-directory permissions
- scheduler hien tai la in-process thread, hop cho MVP nhung chua hop cho deployment nhieu instance

## 15. Huong nang cap tiep

Neu day tiep sau hackathon, uu tien nen la:

1. thay search URL discovery bang matching service that
2. tach scraper va agent ra queue worker
3. dua Postgres + pgvector vao mode chinh
4. them auth, audit log, va deployment
