# TECHNICAL ARCHITECTURE DOC - Guardian Pricing Platform

Audit timestamp: 2026-07-11, workspace local branch state.

This document is a deep technical scan of the current workspace. It covers source code, configuration, ignored runtime artifacts where visible, local logs, fixtures, tests, and current database state.

## 1. TONG QUAN KIEN TRUC & DATA PIPELINE

### 1.1 High-level Architecture

Guardian Pricing Platform is a FastAPI + React pricing intelligence system for monitoring Guardian internal SKUs against competitor marketplace prices. The current architecture is organized around this core loop:

```text
CSV / JSON input
  -> ingestion and fuzzy column mapping
  -> Product + CompetitorLink records
  -> link discovery and URL normalization
  -> Apify or fixture-backed scraper pipeline
  -> platform parser strategies
  -> CompetitorPrice + raw_payload persistence
  -> CPI and alert calculation
  -> Agent briefing and action queue
  -> React dashboard and human approval workflow
```

The backend owns data normalization, scraping, pricing intelligence, alerts, and agent decisions. The frontend owns operator workflows: triggering market queries, inspecting SKU prices, reviewing alerts, running the pricing agent, and approving or rejecting actions.

### 1.2 End-to-end Data Pipeline

#### Step 1 - CSV / JSON Input

There are two ingestion paths:

- `POST /api/v1/products/import-csv` and `POST /api/v1/products/import-dataset` in `backend/app/routes/products.py`
- `POST /api/v1/ingest/upload` in `backend/app/routes/ingest.py`

`products.py` uses `app.services.data_ingestion.import_dataset_from_upload()` for direct CSV/JSON import. It supports field aliases such as `barcode`, `ean`, `product_name`, `title`, `guardian_price`, `selling_price`, `cost_price`, and competitor URL columns such as `shopee_url`, `lazada_url`, `hasaki_url`, and `pharmacity_url`.

`ingest.py` is the more advanced fuzzy mapping route. It uses Pandas to load CSV/JSON, `mapping_config.json` to define possible column names, and `difflib.get_close_matches()` with cutoff `0.82` to map imperfect headers to canonical fields. This preserves important cases such as barcodes with leading zeroes by reading uploaded CSV with `dtype=str`.

#### Step 2 - Normalization and DB Write

`backend/app/services/data_ingestion.py` normalizes records into this canonical product shape:

```text
barcode
name
category
guardian_price
cost_price
image_url
description
competitor_links
```

It uses:

- alias matching via `FIELD_ALIASES`
- numeric cleansing via `_parse_price()`
- duplicate barcode rejection
- transactional reset of operational tables before importing valid rows
- default cost price of roughly `guardian_price * 0.60` when missing

The import then writes:

- `Product`
- optional `CompetitorLink`

The reset clears `AgentAction`, `AgentTask`, `Alert`, `PricingIndex`, `CompetitorPrice`, `CompetitorLink`, and `Product`.

#### Step 3 - Link Discovery

`backend/app/services/link_discovery.py` guarantees that a product has a usable link per platform. The current monitored channels are:

```text
Shopee
Lazada
Pharmacity
Hasaki
```

If a link exists, it is normalized and repaired. If the link has the wrong host or an empty search page, the service rebuilds it from product name and barcode. If no link exists, it creates search-driven URLs:

```text
Shopee      -> https://shopee.vn/search?keyword=...
Lazada      -> https://www.lazada.vn/catalog/?q=...
Pharmacity  -> https://www.pharmacity.vn/search?keyword=...&order=desc&order_by=de-xuat
Hasaki      -> https://hasaki.vn/tim-kiem.html?keyword=...
```

The URL normalizers use `urlparse`, `parse_qs`, `quote`, `unquote`, and regex extraction for detail URL canonicalization:

- Shopee: `-i.shop_id.item_id` or `/product/shop_id/item_id`
- Lazada: `/products/pdp-i{item_id}-s{sku_id}.html`
- Hasaki: `/san-pham/{slug}-{product_id}.html`
- Pharmacity: product `.html` detail pages and `source=/search?...` query recovery

#### Step 4 - Scraper Execution

`backend/app/scraper/scraper_engine.py` is the orchestrator for scraping. It loops through `COMPETITORS = ["Shopee", "Lazada", "Pharmacity", "Hasaki"]`.

For each product/channel pair:

1. `ensure_competitor_link()` obtains or repairs a target URL.
2. `ApifyClientService.run_scraper()` calls Apify if `APIFY_API_TOKEN` exists.
3. If Apify fails or no token exists, fixture fallback loads platform-specific files:
   - `mock_data/apify_fallback_shopee.json`
   - `mock_data/apify_fallback_lazada.json`
   - `mock_data/apify_fallback_pharmacity.json`
   - `mock_data/apify_fallback_hasaki.json`
4. `ScraperFactory.get_scraper(platform)` resolves the parser strategy.
5. Strategy parser emits `CompetitorPriceDTO`.
6. `_pick_best_dto()` chooses the best DTO for the current product.
7. The chosen DTO is converted into a DB price record.
8. `CompetitorPrice` is inserted with `raw_payload` as JSON/JSONB.
9. CPI and alerts are recalculated.

The matching algorithm is token-based:

- Unicode normalization using `unicodedata.normalize("NFKD")`
- ASCII folding and regex tokenization
- token overlap score
- substring bonus
- barcode match bonus
- numeric token bonus for volume/size cues such as `500ml`, `60ml`, `650ml`
- acceptance threshold `0.45`

This is not Levenshtein Distance; it is a weighted token similarity model.

#### Step 5 - Platform Parser Strategies

All platform strategies implement `BaseScraper.parse_to_dto(raw_items, barcode)` and emit the shared `CompetitorPriceDTO` contract.

The DTO is the internal source of truth:

```text
barcode
platform
product_name
shop_name
competitor_price
is_in_stock
promotion_info
raw_payload
```

`raw_payload` is deliberately persisted into `CompetitorPrice.raw_payload`. In PostgreSQL it becomes JSONB; in SQLite it becomes JSON. This is the "lifeboat" field for high-depth scraped attributes that should not break schema migrations, such as voucher detail, branch stock count, actor-specific metadata, model variants, breadcrumb, seller data, ratings, and raw URL.

#### Step 6 - CPI and Alerts

`backend/app/services/cpi_calculator.py` calculates product CPI:

```text
CPI = guardian_price / average_latest_clean_competitor_price * 100
```

It uses only latest clean observations per product/channel from `channel_intelligence.get_latest_channel_observations()`. It filters out:

- `OUT_OF_STOCK`
- missing `net_price`
- suspicious prices

Alert logic:

- Guardian too expensive vs market -> `Overpriced`
- Guardian too cheap vs market -> `Underpriced`
- competitor materially cheaper than Guardian -> `Competitor Undercutting`

Suspicious price detection uses historical deviation:

```text
deviation = abs(new_net_price - avg_last_10_clean_prices) / avg_last_10_clean_prices
```

Deviation above 50% marks the new price as suspicious.

#### Step 7 - API Layer

FastAPI exposes:

```text
/api/v1/products
/api/v1/pricing
/api/v1/alerts
/api/v1/scraper
/api/v1/agent
/api/v1/ingest
/api/sync-price/{barcode}
```

The React UI uses `/api/v1` via `frontend/src/api.js`.

#### Step 8 - React Dashboard

The React dashboard is built with Vite, Axios, Recharts, and Lucide icons.

Main tabs:

- Mission Control: overview, channel CPI, alert feed, agent actions
- SKU Insights: product drill-down, latest competitor table, 7-day chart
- Agent Workspace: task log, action queue, approval workflow, supplier draft modal
- Operations Config: thresholds, upload dataset, demo seed reset

### 1.3 AI Agents

The AI agent architecture is rule-based and graph-orchestrated, with optional Langfuse tracing. It is not currently an LLM-heavy autonomous agent; it is a deterministic decision workflow with agent-shaped boundaries.

#### Market Observer

Files:

- `backend/app/agents/market_observer/market_observer_agent.py`
- `backend/app/agents/market_observer/market_observer_tools.py`

Responsibilities:

- refresh market prices through `run_scraper_for_all_products()`
- select latest clean competitor prices
- choose a reference competitor price for an alert
- build a structured decision context for dashboard briefing

Core algorithm:

- Use latest clean observation per product/channel.
- For `Underpriced`, choose the lowest competitor price above Guardian when possible.
- For competitor undercutting and other alerts, choose the lowest clean competitor price.

#### Margin Guardian

Files:

- `backend/app/agents/margin_guardian/margin_guardian_agent.py`
- `backend/app/agents/margin_guardian/margin_guardian_tools.py`

Responsibilities:

- calculate margin scenarios
- decide whether to match competitor price or negotiate supplier protection
- create `AUTO_PRICE_MATCH` action if margin remains above configured floor

Core algorithm:

```text
current_margin_pct = (guardian_price - cost_price) / guardian_price * 100
margin_if_matched_pct = (competitor_price - cost_price) / competitor_price * 100
price_gap_pct = (guardian_price - competitor_price) / guardian_price * 100
```

Decision rule:

```text
if margin_if_matched_pct >= min_margin:
    strategy = match
else:
    strategy = negotiate
```

It uses LangGraph when available and falls back to a direct sequential pipeline when LangGraph execution fails.

#### Supplier Negotiator

Files:

- `backend/app/agents/supplier_negotiator/supplier_negotiator_agent.py`
- `backend/app/agents/supplier_negotiator/supplier_negotiator_tools.py`

Responsibilities:

- lookup supplier policy context by brand
- generate supplier negotiation email draft
- create `SUPPLIER_EMAIL_DRAFT` action

The policy lookup is currently rule/template based. It includes special handling for La Roche-Posay, Bioderma, Anessa/Shiseido, and default supplier escalation.

#### Orchestrator and Runtime

Files:

- `backend/app/agents/orchestrator/agent_orchestrator.py`
- `backend/app/services/agent_engine.py`
- `backend/app/services/agent_runtime.py`
- `backend/app/agents/shared/runtime_support.py`

Responsibilities:

- create and lock background agent tasks
- optionally refresh market data
- select priority alerts
- run Margin Guardian against each selected alert
- persist `AgentAction`
- expose runtime status and optional Langfuse trace URL

Agent concurrency is guarded with `threading.Lock`.

### 1.4 Runtime State at Scan Time

Current local DB snapshot:

```text
products: 5
competitor_links: 20
competitor_prices: 20
pricing_indices: 5
alerts: 13
agent_tasks: 1
agent_actions: 5
channels: Hasaki=5, Lazada=5, Pharmacity=5, Shopee=5
```

Important anomaly:

```text
All 20 current competitor_prices in the local SQLite DB have net_price = 428507.0 and no raw_payload.
```

This is a runtime data state issue, not a description of the intended code path. The current code includes platform-specific fixtures and parser matching designed to avoid this exact collapse, but the local DB content at scan time is contaminated or stale. Regenerating market data through the current scraper pipeline is required before relying on dashboard values.

## 2. BAN DO CAU TRUC THU MUC

This tree includes source, configuration, hidden folders, ignored artifacts that are visible, and summarized dependency directories.

```text
.
|-- .agents/
|-- .git/
|   |-- refs/
|   |   |-- heads/
|   |   |   |-- main
|   |   |   |-- branch_of_Duy
|   |   |   |-- branch_of_Duy_v2
|   |   |-- remotes/origin/
|-- .pytest_cache/
|-- .venv/
|   |-- Scripts/
|   |-- Lib/site-packages/
|   `-- pyvenv.cfg
|-- backend/
|   |-- app/
|   |   |-- agents/
|   |   |   |-- market_observer/
|   |   |   |   |-- market_observer_agent.py
|   |   |   |   `-- market_observer_tools.py
|   |   |   |-- margin_guardian/
|   |   |   |   |-- margin_guardian_agent.py
|   |   |   |   `-- margin_guardian_tools.py
|   |   |   |-- orchestrator/
|   |   |   |   `-- agent_orchestrator.py
|   |   |   |-- shared/
|   |   |   |   `-- runtime_support.py
|   |   |   `-- supplier_negotiator/
|   |   |       |-- supplier_negotiator_agent.py
|   |   |       `-- supplier_negotiator_tools.py
|   |   |-- core/
|   |   |   `-- mapping_config.json
|   |   |-- db/
|   |   |   |-- models.py
|   |   |   `-- session.py
|   |   |-- routes/
|   |   |   |-- agent.py
|   |   |   |-- alerts.py
|   |   |   |-- ingest.py
|   |   |   |-- pricing.py
|   |   |   |-- products.py
|   |   |   |-- scraper.py
|   |   |   `-- sync.py
|   |   |-- scraper/
|   |   |   |-- mock_scraper.py
|   |   |   `-- scraper_engine.py
|   |   |-- services/
|   |   |   |-- agent_engine.py
|   |   |   |-- agent_runtime.py
|   |   |   |-- apify_client.py
|   |   |   |-- channel_intelligence.py
|   |   |   |-- cpi_calculator.py
|   |   |   |-- daily_scheduler.py
|   |   |   |-- data_ingestion.py
|   |   |   |-- demo_seed.py
|   |   |   |-- link_discovery.py
|   |   |   |-- platform_mappers.py
|   |   |   |-- scraped_samples.py
|   |   |   `-- scrapers/
|   |   |       |-- base.py
|   |   |       |-- factory.py
|   |   |       `-- strategies/
|   |   |           |-- grabmart.py
|   |   |           |-- hasaki.py
|   |   |           |-- lazada.py
|   |   |           |-- pharmacity.py
|   |   |           |-- shopee.py
|   |   |           `-- tiktok.py
|   |   |-- config.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- data/
|   |   |-- knowledge/supplier_policies.txt
|   |   |-- delivery_test/mock_ingest.csv
|   |   |-- delivery_test/mock_ingest.json
|   |   |-- config.json
|   |   |-- apify_fallback_fixture.json
|   |   `-- timestamped ingest snapshots
|   |-- scripts/
|   |   `-- verify_langfuse_tracing.py
|   |-- tests/
|   |   |-- conftest.py
|   |   |-- test_agent_actions.py
|   |   |-- test_agent_decisions.py
|   |   |-- test_alert_routes.py
|   |   |-- test_channel_intelligence.py
|   |   |-- test_demo_seed.py
|   |   |-- test_ingestion_and_mapping.py
|   |   `-- test_product_routes.py
|   |-- guardian.db
|   |-- requirements.txt
|   `-- seed_db.py
|-- data/
|   |-- competitor_mock.csv
|   |-- competitor_scraped_data.csv
|   |-- guardian_internal_sku.csv
|   `-- sku_master.csv
|-- docs/
|   |-- 1.pdf
|   |-- P3.pdf
|   |-- dashboard_preview.png
|   |-- CHANGELOG_UPDATE_2026-07-09.md
|   |-- CONFIG_AND_DEPLOY_GUIDE.md
|   |-- JUDGE_DEMO_RUNBOOK.md
|   |-- pitch_deck_draft.md
|   `-- ĐẶC TẢ BÀI TOÁN HACKATHON.pdf
|-- frontend/
|   |-- node_modules/
|   |-- public/_redirects
|   |-- src/
|   |   |-- pages/
|   |   |   |-- AgentWorkspace.jsx
|   |   |   |-- Configuration.jsx
|   |   |   |-- Overview.jsx
|   |   |   `-- ProductInsights.jsx
|   |   |-- api.js
|   |   |-- App.jsx
|   |   |-- index.css
|   |   `-- main.jsx
|   |-- package.json
|   |-- package-lock.json
|   |-- tsconfig.json
|   `-- vite.config.js
|-- memory-bank/
|-- mock_data/
|   |-- guardian_master_sku.csv
|   |-- apify_fallback_shopee.json
|   |-- apify_fallback_lazada.json
|   |-- apify_fallback_hasaki.json
|   `-- apify_fallback_pharmacity.json
|-- scripts/
|   |-- generate_mock_data.py
|   |-- test_backend.py
|   `-- test_matching_agent.py
|-- .env
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- netlify.toml
|-- README.md
|-- TESTING_GUIDE.md
|-- LOGGING_GUIDE.md
|-- CODEBASE_GUIDE.md
|-- TECHNICAL_EXPLANATION.md
|-- main_branch_health_audit.md
|-- merge_and_refactor_report.md
|-- system_boot_report.md
|-- backend and frontend runtime log files
`-- dataset_shopee-scraper_*.json
```

Ignored but visible runtime artifacts include:

- `.venv/`
- `.pytest_cache/`
- `frontend/node_modules/`
- `backend/guardian.db`
- `*.log`
- `__pycache__/`

These were recognized in the scan but are not expanded line-by-line because they are generated dependencies or runtime state.

## 3. CHI TIET TUNG MODULE & FILE COT LOI

### 3.1 Root Configuration

#### `.env` and `.env.example`

Role:

- runtime settings for DB, Redis, Apify, Langfuse, thresholds, scheduler

Important configuration:

- `USE_SQLITE=True` defaults runtime to `backend/guardian.db`
- `DATABASE_URL` exists for PostgreSQL when SQLite is disabled
- `APIFY_ACTOR_SHOPEE=xtracto/shopee-scraper`
- `APIFY_ACTOR_LAZADA=piotrv1001/lazada-listings-scraper`
- `APIFY_ACTOR_HASAKI=tanduy.work/hasaki-scraper`
- `APIFY_ACTOR_PHARMACITY=tanduy.work/pharmacity-scraper`
- `APIFY_FIXTURE_FALLBACK=True`
- `APIFY_FALLBACK_TO_FIXTURE=True`

#### `docker-compose.yml`

Role:

- local infrastructure for PostgreSQL, Redis, and pgAdmin

Services:

- `db`: `postgres:16-alpine`, exposed on `5432`
- `redis`: `redis:7-alpine`, exposed on `6379`
- `pgadmin`: exposed on `8080`

Current backend config still prefers SQLite unless `USE_SQLITE=False`.

#### `netlify.toml`

Role:

- frontend deployment config

Build:

```text
base = frontend
command = npm run build
publish = dist
```

### 3.2 Backend App Entrypoint

#### `backend/app/main.py`

Role:

- creates FastAPI app
- creates DB tables via `Base.metadata.create_all(bind=engine)`
- applies compatibility schema patches
- mounts routers
- starts/stops daily scheduler
- shuts down Langfuse client on shutdown

Core logic:

- `ensure_compat_schema()` performs defensive `ALTER TABLE` additions for old DBs.
- PostgreSQL path uses `ADD COLUMN IF NOT EXISTS`.
- SQLite path catches exceptions when columns already exist.

Dependencies:

- `settings`
- SQLAlchemy `engine`
- route modules
- `daily_scheduler`
- Langfuse runtime support

Risk:

- It relies on runtime DDL instead of Alembic migrations. This is practical for MVP but fragile for production.

#### `backend/app/config.py`

Role:

- central settings loader
- loads root `.env` first, then `backend/.env` with override
- resolves SQLite vs PostgreSQL database URI
- maps platform to Apify actor IDs
- reads/writes agent config JSON

Core logic:

- `Settings` via `pydantic-settings`
- `field_validator` parses float thresholds even with inline comments
- `sqlalchemy_database_uri` returns SQLite path if `USE_SQLITE=True`
- `get_actor_id_for_platform()` maps normalized platform keys

Dependencies:

- `dotenv`
- `pydantic-settings`
- `backend/data/config.json`

### 3.3 Database Layer

#### `backend/app/db/models.py`

Role:

- SQLAlchemy ORM schema

Core entities:

- `Product`
- `CompetitorLink`
- `CompetitorPrice`
- `PricingIndex`
- `Alert`
- `AgentTask`
- `AgentAction`

Important design:

- `CompetitorPrice.raw_payload = JSON().with_variant(JSONB, "postgresql")`
- product cascades delete to related price, link, index, and alert records
- agent actions have human review statuses: `Pending`, `Approved`, `Rejected`, `Executed`

#### `backend/app/db/session.py`

Role:

- creates SQLAlchemy engine and session factory
- provides FastAPI dependency `get_db()`

Core logic:

- SQLite uses `check_same_thread=False`
- all DB access goes through `SessionLocal`

### 3.4 Schemas

#### `backend/app/schemas.py`

Role:

- Pydantic response/request contracts

Important DTOs:

- `Product`, `ProductDetail`
- `CompetitorPrice`
- `PricingIndex`
- `Alert`
- `OverviewStats`
- `ChannelIntelligence`
- `AgentBriefing`
- `ScrapeSample`

The frontend relies heavily on these exact keys: `net_price`, `raw_price`, `stock_status`, `is_suspicious`, `voucher_details`, `promo_mechanics`, `raw_payload`, `competitor_index`, `channel`, `cpi`, `coverage_pct`, and `priority_queue`.

### 3.5 Ingestion

#### `backend/app/routes/ingest.py`

Role:

- advanced upload endpoint at `/api/v1/ingest/upload`
- saves original upload into `backend/data/{timestamp}_{filename}`
- maps headers using Pandas + fuzzy matching
- sends normalized bytes to `import_dataset_from_upload()`

Algorithms:

- `difflib.get_close_matches()` for fuzzy header matching
- regex filename sanitization
- Pandas `read_csv(..., dtype=str, keep_default_na=False)` to preserve leading-zero barcodes
- JSON payload conversion to DataFrame

Dependencies:

- `pandas`
- `mapping_config.json`
- `data_ingestion.import_dataset_from_upload`

#### `backend/app/services/data_ingestion.py`

Role:

- canonical product import service

Algorithms:

- alias mapping via `FIELD_ALIASES`
- price parsing with separator detection
- validation and duplicate barcode detection
- operational table reset

Dependencies:

- SQLAlchemy models
- Python `csv`, `json`, `io`

Risk:

- `_reset_operational_tables()` is intentionally destructive for demo imports. In production this should become a versioned batch import or soft replacement.

#### `backend/app/core/mapping_config.json`

Role:

- declares fuzzy candidates for barcode, product name, and price

Example:

- barcode candidates: `barcode`, `ean`, `ean-13`, `upc`, `sku_code`
- product name candidates: `product_name`, `name`, `title`, `description`
- price candidates: `price`, `cost`, `unit_price`, `retail_price`

### 3.6 Link Discovery

#### `backend/app/services/link_discovery.py`

Role:

- builds search URLs
- canonicalizes imported or scraped competitor URLs
- repairs existing dirty links in DB

Algorithms:

- platform-specific URL builders
- regex detail URL extraction
- host validation by expected domain
- fallback rebuild if URL is wrong host or empty search page
- Unicode text normalization helper

Dependencies:

- SQLAlchemy `Session`
- `Product`, `CompetitorLink`
- `urllib.parse`
- regex

Important behavior:

- If DB holds a Lazada link that points to Hasaki, it is rejected and rebuilt as a Lazada search URL.
- If Pharmacity link is `/tim-kiem` without query, it is rejected and rebuilt with keyword.

### 3.7 Scraper Core

#### `backend/app/scraper/scraper_engine.py`

Role:

- orchestrates all product/channel scrape runs
- chooses best parsed DTO
- persists competitor prices
- triggers CPI recomputation

Algorithms:

- async wrapper with event loop compatibility
- weighted token matching
- barcode and numeric token scoring
- suspicious price checking via CPI service
- deterministic fallback price generator
- pre-upsert raw payload logging

Dependencies:

- `ApifyClientService`
- `ScraperFactory`
- `ensure_competitor_link`
- `calculate_cpi_for_product`
- `check_price_anomaly`

Risk:

- Full scrape is currently sequential across products/channels; production scale will need queue workers or async fan-out.

#### `backend/app/services/apify_client.py`

Role:

- Apify actor runner
- fixture fallback selector

Algorithms:

- start Apify actor
- poll run status until `SUCCEEDED`, `FAILED`, `ABORTED`, or timeout
- list default dataset items
- collect platform-specific fixture candidates
- filter generic fixture items by `platform`
- dedupe fixture items by platform, barcode, title/name, URL, item ID, shop ID

Dependencies:

- `apify-client`
- `settings.APIFY_FIXTURE_FALLBACK`
- `mock_data/apify_fallback_*.json`
- root Shopee dataset JSON as legacy fixture

#### `backend/app/services/scrapers/base.py`

Role:

- parser strategy interface and shared DTO

Algorithms:

- `clean_price_string()` normalizes VND price strings and thousand separators
- Pydantic DTO validation

#### `backend/app/services/scrapers/factory.py`

Role:

- registry mapping platform keys to scraper classes

Registered:

- `shopee`
- `lazada`
- `tiktok`
- `tiktok_shop`
- `grabmart`
- `hasaki`
- `pharmacity`

Current orchestrated runtime only uses Shopee, Lazada, Pharmacity, Hasaki.

### 3.8 Platform Strategies

#### `strategies/shopee.py`

Role:

- parse `xtracto/shopee-scraper` payloads into `CompetitorPriceDTO`

Algorithms:

- product name from `title` or `name`
- price uses Shopee divisor `100_000` only when raw numeric price is above `1_000_000`
- stock from `availability` or `stock_status`
- promotion from `discount_pct`
- product URL built from breadcrumb or `shop_id/item_id`

Dependencies:

- `clean_price_string`
- regex

#### `strategies/lazada.py`

Role:

- parse Lazada payloads

Algorithms:

- product name from `name`, `title`, or `product_name`
- plain VND price parse
- stock from `inStock`
- promotion from `discount` or `discount_pct`
- URL reconstruction from `itemId` and `skuId`

#### `strategies/hasaki.py`

Role:

- parse Hasaki payloads

Algorithms:

- product name from `title` or `name`
- price from `current_price` or `price`
- stock from Vietnamese/English stock status
- promotion list flattening

#### `strategies/pharmacity.py`

Role:

- parse Pharmacity payloads that may lack explicit `title`

Algorithms:

- product name priority: `title`, `name`, `product_name`, hierarchy tail, URL slug, `source` search keyword
- price from `current_price` or `price`
- URL reconstruction from raw URL, source path, or slugified product name
- stock and promotion normalization

#### `strategies/tiktok.py` and `strategies/grabmart.py`

Role:

- future/legacy parser support

Current status:

- registered in factory
- not part of active `COMPETITORS` in `scraper_engine.py`
- fixtures for these are not the main demo path

### 3.9 Pricing Intelligence

#### `backend/app/services/channel_intelligence.py`

Role:

- channel-level scorecard for dashboard

Algorithms:

- SQL `row_number()` window partitioned by product and competitor to choose latest deterministic row
- coverage calculation
- freshness SLA calculation
- promotion, voucher, bundle, flash sale counts
- market position classification: `guardian_premium`, `guardian_value`, `parity`

Dependencies:

- SQLAlchemy window function
- settings thresholds
- agent config

#### `backend/app/services/cpi_calculator.py`

Role:

- product-level CPI and alert generation

Algorithms:

- latest clean competitor observation filtering
- CPI average
- threshold-based recommendation
- unresolved alert reset per product
- historical anomaly detection over last 10 clean prices

### 3.10 API Routes

#### `routes/products.py`

Role:

- product CRUD
- CSV/JSON import
- load default catalog from `mock_data/guardian_master_sku.csv`
- seed large demo dataset from `data/sku_master.csv`

Dependency surface:

- `data_ingestion`
- `demo_seed`
- `calculate_cpi_for_product`

#### `routes/scraper.py`

Role:

- manual scrape trigger
- in-memory scrape status
- default catalog load before scraping
- branch sample endpoint

Important behavior:

- `POST /api/v1/scraper/trigger` with `{ "load_default_catalog": true }` reloads `mock_data/guardian_master_sku.csv` and runs scrape in a FastAPI background task.

Risk:

- status is in-memory and resets on process restart.

#### `routes/sync.py`

Role:

- single-barcode sync endpoint at `/api/sync-price/{barcode}`

Note:

- This router is mounted at prefix `/api`, not `/api/v1`, so the real route is `/api/sync-price/{barcode}`.

#### `routes/pricing.py`

Role:

- overview metrics
- channel intelligence
- product CPI table with latest competitor price map

#### `routes/alerts.py`

Role:

- alert feed sorted by business severity
- alert resolution

#### `routes/agent.py`

Role:

- agent run trigger
- briefing
- task/action history
- action approve/reject
- config save/load
- runtime status

Approval behavior:

- `AUTO_PRICE_MATCH` changes `Product.guardian_price`, resolves alerts, and recalculates CPI.
- `SUPPLIER_EMAIL_DRAFT` is reviewable but not auto-sent.

### 3.11 Agent Services

#### `services/agent_engine.py`

Role:

- public import bridge for agent loop and decision context

#### `services/agent_runtime.py`

Role:

- creates pending task
- guards concurrent runs with lock
- starts agent loop in background
- tracks last run metadata and Langfuse trace URL

#### `services/daily_scheduler.py`

Role:

- in-process daily background scheduler

Algorithm:

- daemon thread waits `AGENT_SCHEDULE_INTERVAL_SECONDS`, minimum 60 seconds
- skips if an agent run is already active
- creates scheduler task and runs agent with `refresh_market_data=True`

Risk:

- in-process scheduler is fine for a hackathon MVP but not safe for multi-instance deployment.

### 3.12 Frontend Modules

#### `frontend/src/api.js`

Role:

- computes `API_BASE_URL`

Default:

```text
http://localhost:8001/api/v1
```

#### `frontend/src/App.jsx`

Role:

- main shell and navigation
- polling for scraper status, latest task status, and alerts
- lazy-loads page modules

Dependencies:

- React lazy/Suspense
- Axios
- Lucide icons

#### `frontend/src/pages/Overview.jsx`

Role:

- mission control dashboard
- market query button
- run agent button
- KPI cards, channel CPI chart, promotions, alerts, recent actions

API calls:

- `GET /pricing/overview`
- `GET /alerts`
- `GET /agent/briefing?limit=5`
- `GET /agent/actions?limit=5`
- `GET /pricing/channel-index`
- `POST /scraper/trigger`
- `POST /agent/run`
- `POST /alerts/{id}/resolve`

Important behavior:

- `handleTriggerScrape()` posts `{ load_default_catalog: true }`, so the dashboard query path uses `mock_data/guardian_master_sku.csv`.

#### `frontend/src/pages/ProductInsights.jsx`

Role:

- SKU drill-down
- competitor net-price table
- price history chart

API calls:

- `GET /pricing/cpi-index`
- `GET /products/{id}`

Algorithms:

- groups price history by date
- latest row per competitor by timestamp then ID
- computes gap vs Guardian client-side for display

#### `frontend/src/pages/AgentWorkspace.jsx`

Role:

- agent terminal log
- task polling
- action queue
- supplier email modal
- approve/reject price match actions

API calls:

- `GET /agent/tasks`
- `GET /agent/actions`
- `GET /agent/briefing`
- `GET /agent/runtime-status`
- `POST /agent/run`
- `POST /agent/actions/{id}/approve`
- `POST /agent/actions/{id}/reject`

#### `frontend/src/pages/Configuration.jsx`

Role:

- tune agent thresholds
- import CSV/JSON dataset
- seed demo dataset

API calls:

- `GET /agent/config`
- `POST /agent/config`
- `POST /products/import-dataset`
- `POST /products/seed-demo`

#### `frontend/src/index.css`

Role:

- app-wide design system and responsive layout

Style characteristics:

- `Manrope` and `IBM Plex Mono`
- operator-console layout with fixed sidebar
- Recharts containers
- responsive single-column collapse below 1180px

### 3.13 Data Assets

#### `mock_data/guardian_master_sku.csv`

Role:

- current 5-SKU default catalog used by dashboard `Query market data`

Fields:

- `barcode`
- `product_name`
- `category`
- `guardian_price`
- `cost_price`

#### `mock_data/apify_fallback_*.json`

Role:

- platform-specific scraper fixtures
- each file contains the same 5 barcodes for full 4-channel demo coverage

These files allow the parsing/matching pipeline to behave like real Apify output when there is no Apify token or actor call fails.

#### `data/sku_master.csv` and `data/competitor_mock.csv`

Role:

- larger seeded demo dataset used by `seed_demo_dataset()`
- test expects 200 SKUs, 8400 competitor price rows, 1200 links, 6 channels

This is separate from the dashboard query path that reloads `mock_data/guardian_master_sku.csv`.

#### `backend/data/apify_fallback_fixture.json`

Role:

- legacy generic fallback fixture

Risk:

- Generic mixed-platform fixture can contaminate platform parsing if not filtered. `ApifyClientService` now filters generic fixture items by platform.

### 3.14 Tests

Tests use in-memory SQLite via `StaticPool`.

Coverage:

- upload validation preserves existing catalog on invalid input
- Vietnamese price thousand parsing
- duplicate barcode reporting
- static route `/seed-demo` avoids being captured by product ID route
- channel CPI uses latest clean observation
- alert feed orders by severity
- agent reference price selection ignores stale/suspicious rows
- approving price match recalculates CPI
- demo seed dataset shape

Gaps:

- no frontend tests
- no live Apify contract tests
- no end-to-end browser test
- no regression test for the `428507` collapse
- no test asserting platform-specific fixtures produce 20/20 valid observations

## 4. TRANG THAI HIEN TAI & ROADMAP

### 4.1 Completed / Strong Areas

- FastAPI app is structured by domain routes and services.
- SQLAlchemy schema has enough depth for products, links, prices, CPI, alerts, tasks, and actions.
- CSV/JSON ingestion supports aliases, fuzzy header mapping, and leading-zero barcode preservation.
- Link discovery now has platform-specific URL canonicalization and host guards.
- Scraper OOP strategy pattern is in place through `BaseScraper`, `ScraperFactory`, and `strategies/*`.
- `raw_payload` JSON/JSONB protects schema from actor-specific data changes.
- Channel intelligence uses deterministic latest-row selection with SQL window functions.
- Agent workflow is separated into Observer, Guardian, Negotiator, Orchestrator, and Runtime.
- Human approval is enforced before applying price changes.
- Frontend dashboard is connected to real backend endpoints and can trigger scrape/agent runs.
- Platform-specific mock fixtures exist for full 4-channel demo coverage.

### 4.2 Current Bottlenecks / Risks

- Local DB state at scan time is contaminated: all 20 current competitor price rows are `428507.0` with no `raw_payload`.
- Runtime schema changes are handled through defensive `ALTER TABLE`, not Alembic migrations.
- Scraper execution is sequential and in-process.
- Background scraper and scheduler state are stored in memory.
- Apify live actor input schemas are generic and may need actor-specific payload formats.
- TikTok Shop and GrabMart are registered but not active in the current 4-channel runtime.
- The large `data/sku_master.csv` seed path and `mock_data/guardian_master_sku.csv` query path can confuse operators if they do not know which button loads which dataset.
- Existing tests do not yet lock down the current platform-specific fixture behavior.
- Frontend uses polling, not server-sent events or websocket updates.
- No auth, RBAC, audit log, or multi-user approval controls.

### 4.3 Three Next Coding Steps for a Complete E2E Demo

1. Add a deterministic "refresh clean demo data" endpoint.

   This endpoint should load `mock_data/guardian_master_sku.csv`, clear stale `CompetitorPrice`, run the 4-channel scraper, verify `raw_payload.platform` coverage, and return a compact QA summary:

   ```text
   products = 5
   expected_observations = 20
   actual_observations = 20
   fallback_count = 0
   price_428507_count = 0
   channels = Shopee/Lazada/Pharmacity/Hasaki
   ```

   This would remove ambiguity between contaminated runtime DB state and code capability.

2. Add regression tests for platform-specific fixture and scraper matching.

   Tests should assert:

   - each `mock_data/apify_fallback_{platform}.json` has all catalog barcodes
   - `ApifyClientService(platform_key=...)` only returns matching platform rows
   - `run_scraper_for_all_products()` creates 20 records for 5 SKUs
   - no latest row has `net_price == 428507`
   - every latest row has `raw_payload.platform`

3. Add dashboard scrape completion polling and raw payload inspection.

   Frontend should poll `/scraper/status` after `Query market data`, then refresh overview and SKU data when `is_running=false`. Add a raw payload drawer in `ProductInsights` so the category manager can inspect the exact scraped JSON per channel without leaving the UI.

### 4.4 Production Roadmap After Demo

- Introduce Alembic migrations.
- Move scraper/agent jobs into a queue worker such as Celery/RQ/Arq.
- Store scrape job runs in DB, not in memory.
- Add actor-specific Apify run inputs per platform.
- Add live actor contract tests with recorded fixtures.
- Add auth and approval audit trail.
- Split demo fixture mode from live scraping mode in UI.
- Add frontend tests for dashboard rendering and action approval.
- Add observability dashboards around scrape success rate, fallback rate, actor latency, and parser rejection reasons.

## 5. Quick Operator Notes

To inspect current backend data:

```powershell
Get-Content .\backend_boot.out.log -Wait
```

To filter scraper evidence:

```powershell
Select-String -Path .\backend_boot.out.log -Pattern "Pre-upsert competitor payloads|fallback|Rejected scraper payload"
```

To trigger dashboard scrape from UI:

```text
Mission Control -> Query market data
```

This sends:

```json
{
  "load_default_catalog": true
}
```

to:

```text
POST /api/v1/scraper/trigger
```

## 6. Final Assessment

The current codebase is a strong hackathon-stage architecture with a coherent backend domain model, a working React command center, a practical OOP scraper layer, and a meaningful agent workflow. The biggest issue is not architectural shape; it is operational hygiene around runtime data state, migration discipline, and job orchestration.

The system is demo-capable once DB state is regenerated cleanly through the current scraper path. It is not yet production-ready without migrations, queue workers, stronger live scraper contracts, and audit-grade approval controls.
