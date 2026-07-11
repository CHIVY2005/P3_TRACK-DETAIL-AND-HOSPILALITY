# CODEBASE GUIDE

Tai lieu nay mo ta codebase theo goc nhin kien truc va ownership: file nao giu vai tro gi, sua cho nao khi muon mo rong, va luong du lieu chay qua cac module nhu the nao.

## 1. Ban do repo

```text
backend/
  app/
    agents/        agent architecture moi
    db/            SQLAlchemy session + models
    routes/        REST APIs
    scraper/       hybrid scraping runtime
    services/      ingestion, pricing, seed, adapters
    config.py
    schemas.py
    main.py
  data/            config va knowledge files

frontend/
  src/
    pages/         4 man hinh chinh
    App.jsx        app shell
    index.css      design system + layout

scripts/           test va mock data scripts
data/              CSV demo
docs/              docs cho pitch, deploy, architecture
```

## 2. Backend entrypoints

### `backend/app/main.py`

Entry point cua FastAPI. File nay:

1. tao app
2. bat CORS
3. auto create tables
4. dang ky routers:
   - `products`
   - `pricing`
   - `alerts`
   - `scraper`
   - `agent`
   - `sync`

Neu mot route moi khong hien len `/docs`, day la noi can kiem tra dau tien.

### `backend/app/config.py`

Giu:

- bien moi truong
- config database
- config scraper
- threshold mac dinh
- doc / ghi `backend/data/config.json`

Hai ham quan trong:

- `get_agent_config()`
- `save_agent_config()`

## 3. Database layer

### `backend/app/db/session.py`

Giu:

- `engine`
- `SessionLocal`
- `Base`
- dependency `get_db()`

### `backend/app/db/models.py`

Day la schema trung tam cua toan he thong.

#### `Product`

Catalog san pham noi bo:

- `barcode`
- `name`
- `category`
- `guardian_price`
- `cost_price`
- `image_url`
- `description`

#### `CompetitorLink`

Bang moi de giu link doi thu theo tung product:

- `product_id`
- `platform`
- `url`
- `discovery_method`

Bang nay cho phep ingestion, discovery, va scrape that noi voi nhau.

#### `CompetitorPrice`

Moi lan doc duoc gia doi thu se tao 1 record:

- `competitor_name`
- `raw_price`
- `discount`
- `net_price`
- `stock_status`
- `is_suspicious`
- `voucher_details`
- `promo_mechanics`
- `url`
- `scraped_at`

#### `PricingIndex`

Ket qua tinh toan CPI cho tung product:

- `competitor_index`
- `average_competitor_price`
- `recommendation`

#### `Alert`

Tin hieu business de agent va dashboard su dung:

- `alert_type`
- `message`
- `severity`
- `is_resolved`

#### `AgentTask`

Phien chay cua agent:

- `objective`
- `status`
- `logs`

#### `AgentAction`

Hanh dong agent tao ra:

- `AUTO_PRICE_MATCH`
- `SUPPLIER_EMAIL_DRAFT`

## 4. Routes

### `backend/app/routes/products.py`

Ownership:

- CRUD product
- import dataset
- seed demo dataset

Diem can nho:

- route cu `import-csv` van duoc giu de tuong thich
- route moi `import-dataset` ho tro ca `csv` va `json`

### `backend/app/routes/pricing.py`

Ownership:

- `overview` cho KPI top-level
- `cpi-index` cho danh sach SKU va CPI

### `backend/app/routes/alerts.py`

Ownership:

- list alert
- resolve alert

### `backend/app/routes/scraper.py`

Ownership:

- trigger scrape background
- xem status scrape
- doc scrape evidence tu branch crawl

### `backend/app/routes/agent.py`

Ownership:

- trigger agent run
- list task va actions
- expose `agent/briefing`
- expose runtime + scheduler status
- approve / reject action
- doc / ghi config

### `backend/app/routes/sync.py`

Ownership:

- sync gia theo barcode va platform
- noi `Product` -> `CompetitorLink` -> scrape -> `CompetitorPrice`

Route nay la cau noi truc tiep nhat giua ingestion va huong crawl data.

## 5. Services

### `backend/app/services/data_ingestion.py`

MVP ingestion engine.

Nhiem vu:

1. doc `csv` hoac `json`
2. tu map field aliases
3. tao `Product`
4. tao `CompetitorLink` neu co URL
5. reset cac bang van hanh truoc khi import

Sua file nay neu:

- format file moi can support
- muon them field aliases
- muon doi chinh sach reset khi import

### `backend/app/services/link_discovery.py`

Nhiem vu:

- tao search-driven competitor link neu product chua co URL
- giu lai logic theo tung platform

Sua file nay neu:

- muon them platform moi
- muon doi kieu discovery
- muon tich hop matching service that

### `backend/app/services/platform_mappers.py`

Nhiem vu:

- chuan hoa payload raw scrape thanh schema noi bo
- gop ten truong khac nhau tu marketplace ve mot shape chung

### `backend/app/services/cpi_calculator.py`

Pricing engine cot loi.

Ham quan trong:

- `calculate_cpi_for_product()`
- `generate_alerts_for_product()`
- `check_price_anomaly()`

Sua file nay neu can doi logic CPI, threshold behavior, hoac anomaly detection.

### `backend/app/services/demo_seed.py`

Reset du lieu demo:

- xoa bang cu
- doc `data/sku_master.csv`
- doc `data/competitor_mock.csv`
- insert lai data
- tinh CPI va alerts

### `backend/app/services/startup_bootstrap.py`

Khoi tao fresh clone an toan:

- dem product truoc khi seed
- chi seed khi catalog rong
- chi chay o development/demo/local/test
- khong ghi de catalog da import
- tra bootstrap status qua root health endpoint

Dieu khien bang `ENV` va `AUTO_SEED_DEMO`.

### `backend/app/services/scraped_samples.py`

Doc scrape evidence tu file JSON branch crawl.

Nhiem vu:

- mo file raw
- chuan hoa title, price, url
- thu match listing voi catalog hien tai

### `backend/app/services/agent_engine.py`

File nay khong con la logic lon nua. No da tro thanh compatibility layer:

- re-export `build_alert_decision_context`
- re-export `run_agentic_optimization_loop`

Muc dich la de route cu va code khac khong bi gay.

### `backend/app/services/agent_runtime.py`

Nhiem vu:

- tao `AgentTask`
- giu lock de tranh manual run va scheduled run chong len nhau
- luu runtime status cua agent

### `backend/app/services/daily_scheduler.py`

Nhiem vu:

- khoi dong scheduler cung app
- moi 1 ngay chay 1 autonomous cycle
- refresh market data truoc khi reasoning
- bo qua tick neu agent dang chay

## 6. Agents

### `agents/market_observer`

Day la lop doc signal thi truong cho dashboard va orchestrator.

Quan ly:

- lay latest clean competitor price
- bien 1 alert thanh decision context de frontend doc duoc

### `agents/margin_guardian`

Day la lop quyet dinh chinh.

Quan ly:

- tinh current margin
- tinh margin if matched
- chon `match` hay `negotiate`
- tao action `AUTO_PRICE_MATCH`

### `agents/supplier_negotiator`

Quan ly:

- lookup supplier policy
- tao email draft
- tao action `SUPPLIER_EMAIL_DRAFT`

### `agents/orchestrator`

Quan ly:

- khoi tao `AgentTask`
- option refresh market data
- loop unresolved alerts
- goi margin guardian / supplier negotiator
- persist actions va logs

### `agents/shared/runtime_support.py`

Quan ly:

- append logs
- append tool events
- run tool wrapper
- Langfuse client / callback

### `agents/orchestrator` va scheduler

`orchestrator` la noi quyet dinh 1 phien chay agent lam gi.

`daily_scheduler.py` la noi quyet dinh khi nao phien chay do duoc kich hoat tu dong.

## 7. Scraper layer

### `backend/app/scraper/scraper_engine.py`

Trung tam scrape.

Modes:

- `scrape_via_apify()`
- `scrape_via_crawl4ai()`
- `scrape_via_playwright()`
- `simulate_competitor_price()`

Flow:

1. lay product
2. dam bao co `CompetitorLink`
3. thu scrape theo channel
4. map payload raw ve schema chung
5. check anomaly
6. save `CompetitorPrice`
7. recalculate CPI

## 8. Frontend

### `frontend/src/App.jsx`

App shell:

- nav 4 tab
- poll scraper status
- poll latest agent status
- hien open alert count

### `frontend/src/pages/Overview.jsx`

Man tong quan:

- Top 200 SKU scorecard
- omnichannel CPI voi parity = 100
- automation coverage va freshness 24 gio
- decision audit trail
- priority decisions khong lap SKU
- promotion intelligence theo voucher / bundle / flash sale
- alert feed
- recent actions

### `frontend/src/pages/ProductInsights.jsx`

Man drill-down:

- search SKU
- chon product
- xem metric card
- bang net price
- chart lich su gia

### `frontend/src/pages/AgentWorkspace.jsx`

Man operator:

- run agent
- xem terminal logs
- xem action queue
- approve / reject
- doc supplier draft
- xem task history

### `frontend/src/pages/Configuration.jsx`

Man van hanh:

- chinh thresholds
- upload dataset CSV/JSON
- reset demo

### `frontend/src/index.css`

Day la design system chinh:

- color tokens
- layout shell
- cards
- data table
- terminal shell
- modal
- responsive rules

## 9. File nen sua theo nhu cau

Neu muon:

- doi logic import dataset: `services/data_ingestion.py`
- doi discovery strategy: `services/link_discovery.py`
- doi scrape mapping: `services/platform_mappers.py`
- doi logic CPI: `services/cpi_calculator.py`
- doi read model CPI da kenh: `services/channel_intelligence.py`
- doi agent decision: `agents/margin_guardian/`
- doi supplier workflow: `agents/supplier_negotiator/`
- doi dashboard tong quan: `frontend/src/pages/Overview.jsx`
- doi shell toan app: `frontend/src/App.jsx`
- doi visual system: `frontend/src/index.css`

## 10. Phan nao on dinh, phan nao la MVP

On dinh de demo:

- seed demo
- import dataset
- CPI + alert engine
- CPI / coverage / freshness theo tung kenh
- agent approval flow
- dashboard views
- production frontend build
- backend test suite 200 SKU

MVP / can nang cap tiep:

- matching link doi thu production-grade
- queue worker
- auth
- deployment production
- scheduler hien tai la in-process thread, chua phai distributed scheduler
