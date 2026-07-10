# GUARDIAN Pricing Command Center

GUARDIAN la mot MVP cho bai toan theo doi gia doi thu, tinh chi so CPI, va de xuat hanh dong dieu chinh gia theo vong:

`Ingest -> Discover -> Scrape -> Analyze -> Decide -> Approve`

He thong hien tai da hop nhat 2 huong phat trien:

- `main`: dashboard, alert engine, agent workspace, human approval
- `branch_of_Duy`: huong crawl data that, sync gia, va data evidence

Ket qua la mot codebase co the demo duoc ngay, dong thoi mo rong tiep thanh pipeline production sau hackathon.

## 1. Muc tieu san pham

GUARDIAN giai quyet 4 van de chinh:

1. Khi du lieu noi bo chi moi co barcode, ten san pham, gia ban thi phai nap vao he thong the nao.
2. Khi chua co link Shopee, Hasaki, Lazada thi phai tim link doi thu the nao.
3. Khi can cap nhat gia doi thu thi he thong co the scrape theo lo, thay vi nguoi dung bam tung SKU.
4. Khi AI de xuat match gia thi van phai giu quyen phe duyet cho con nguoi.

## 2. Kien truc tong quan

```text
Frontend React
  -> hien Mission Control, SKU Insights, Agent Workspace, Configuration

FastAPI Backend
  -> Products / Pricing / Alerts / Scraper / Agent / Sync APIs
  -> import dataset CSV/JSON
  -> discover competitor links
  -> scrape hybrid
  -> calculate CPI
  -> tao alert
  -> chay agent va approval workflow

SQLite / PostgreSQL-compatible schema
  -> Product
  -> CompetitorLink
  -> CompetitorPrice
  -> PricingIndex
  -> Alert
  -> AgentTask
  -> AgentAction
```

## 3. Kien truc agent moi

Phan agent da duoc tach thanh cac folder theo vai tro:

```text
backend/app/agents/
  market_observer/
    market_observer_agent.py
    market_observer_tools.py
  margin_guardian/
    margin_guardian_agent.py
    margin_guardian_tools.py
  supplier_negotiator/
    supplier_negotiator_agent.py
    supplier_negotiator_tools.py
  orchestrator/
    agent_orchestrator.py
  shared/
    runtime_support.py
```

Y nghia tung agent:

- `Market Observer`: doc alert, lay gia doi thu hop le, tao decision context cho dashboard
- `Margin Guardian`: tinh margin, quyet dinh `match` hay `negotiate`
- `Supplier Negotiator`: tra policy theo rule/template, tao email draft
- `Orchestrator`: dieu phoi toan bo vong chay agent
- `Shared runtime`: log, Langfuse tracing client, tool execution wrapper

## 4. Luong du lieu end-to-end

### 4.1 Dynamic ingestion

Nguoi dung upload `csv` hoac `json` qua:

- `POST /api/v1/products/import-dataset`
- alias cu van duoc giu: `POST /api/v1/products/import-csv`

Importer se:

1. Tu map cac cot pho bien nhu `barcode`, `name`, `guardian_price`, `cost_price`
2. Tu nhan dien URL doi thu neu file co cac cot nhu `shopee_url`, `hasaki_url`, `lazada_url`
3. Tao `Product`
4. Tao `CompetitorLink` neu co URL san
5. Sau do kich hoat scrape MVP cho tung SKU

### 4.2 Link discovery

Neu san pham chua co link doi thu, service `link_discovery.py` se tao search URL theo platform:

- Shopee
- Lazada
- TikTok Shop
- GrabMart
- Pharmacity
- Hasaki

Muc tieu cua MVP la dam bao he thong luon co mot diem bat dau de scrape, ke ca khi du lieu dau vao chua day du.

### 4.3 Hybrid scraping

`scraper_engine.py` hien tai ket hop nhieu che do:

- `Apify` cho marketplace
- `Playwright` cho trang can render JS
- `Crawl4AI` cho search page / web content
- `simulate_competitor_price()` lam fallback

Neu scrape that that bai, he thong van tra duoc du lieu fallback de pipeline demo khong bi dung.

### 4.4 Pricing intelligence

Sau moi lan ghi `CompetitorPrice`, he thong:

1. Loai bo record `OUT_OF_STOCK`, `net_price = None`, va `is_suspicious = True`
2. Tinh `average_competitor_price`
3. Tinh `CPI = guardian_price / average_competitor_price * 100`
4. Tao `PricingIndex`
5. Tao `Alert`

### 4.5 Agent + human approval

Agent chay theo luong:

1. Co the refresh market data
2. Lay unresolved alerts
3. Tinh margin hien tai va margin neu match gia
4. Chon `match` hoac `negotiate`
5. Tao `AgentAction`
6. Nguoi dung approve / reject

`AUTO_PRICE_MATCH` chi duoc ap dung khi nguoi dung approve.

### 4.6 Daily autonomous cycle

Theo brief `hybrid scheduler`, backend hien tai da co scheduler chay ngam moi `86400` giay, tuc `1 ngay`.

Moi chu ky, he thong se:

1. refresh market data
2. tinh lai CPI va alerts
3. chay agent orchestration
4. tao recommendation moi neu co case can xu ly

Trang thai agent va scheduler co the xem qua:

- `GET /api/v1/agent/runtime-status`

## 5. Frontend

Frontend da duoc doi thanh mot shell van hanh ro rang hon:

- `Mission Control`: overview va decision queue
- `SKU Insights`: drill-down tung san pham
- `Agent Workspace`: run agent, xem logs, approve actions
- `Operations Config`: threshold, upload dataset, seed demo

Mac dinh frontend goi backend tai:

```text
http://localhost:8001/api/v1
```

Co the doi qua env:

```text
VITE_API_ORIGIN=http://localhost:8001
```

## 6. API quan trong

### Products

- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products`
- `PUT /api/v1/products/{product_id}`
- `POST /api/v1/products/import-dataset`
- `POST /api/v1/products/import-csv`
- `POST /api/v1/products/seed-demo`

### Pricing

- `GET /api/v1/pricing/overview`
- `GET /api/v1/pricing/cpi-index`

### Alerts

- `GET /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/resolve`

### Scraper

- `POST /api/v1/scraper/trigger`
- `GET /api/v1/scraper/status`
- `GET /api/v1/scraper/branch-samples`

### Agent

- `POST /api/v1/agent/run`
- `GET /api/v1/agent/briefing`
- `GET /api/v1/agent/tasks`
- `GET /api/v1/agent/actions`
- `GET /api/v1/agent/runtime-status`
- `POST /api/v1/agent/actions/{action_id}/approve`
- `POST /api/v1/agent/actions/{action_id}/reject`
- `GET /api/v1/agent/config`
- `POST /api/v1/agent/config`

### Omnichannel intelligence

- `GET /api/v1/pricing/channel-index`
  - CPI theo tung kenh, voi `100` la parity
  - coverage tren catalog 200 SKU
  - freshness SLA 24 gio
  - data quality, voucher, bundle, flash sale va pricing opportunity

### Sync

- `POST /api/sync-price/{barcode}?platform=Hasaki`

## 7. Chay du an

### Backend

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\activate
pip install -r backend\requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Docs:

```text
http://127.0.0.1:8001/docs
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

App:

```text
http://localhost:3000
```

## 8. Trang thai hien tai

Da co:

- dynamic ingestion CSV/JSON
- competitor link registry
- search-driven link discovery
- hybrid scrape fallback
- CPI + alert engine
- agent architecture tach folder ro rang
- daily autonomous scheduler 1 ngay / lan
- human approval workflow
- UI dashboard moi theo kieu operator console
- scorecard bam sat `P3.pdf`: 200 SKU, 6 kenh, CPI theo kenh, freshness va promotion intelligence
- bo test backend chay full seed 200 SKU

Con gioi han:

- link discovery hien tai la MVP theo search URL, chua phai catalog matching production-grade
- chua co queue worker, auth, audit log, va deployment production
- scheduler hien tai la in-process background thread, hop cho MVP nhung chua phai distributed scheduler

## 9. Kiem thu

```powershell
cd backend
..\.venv312\Scripts\python.exe -m pytest -q

cd ..\frontend
npm.cmd run build
```

Bo test hien tai kiem tra:

- CPI theo kenh chi dung latest clean observation
- effective price sau voucher
- import transactional va parse gia VND
- agent chon dung market reference
- static seed route khong bi route product ID bat nham
- full seed dung 200 SKU, 8.400 price rows, 1.200 links va 6 kenh

## 10. Tai lieu nen doc tiep

- [CODEBASE_GUIDE.md](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/CODEBASE_GUIDE.md)
- [TECHNICAL_EXPLANATION.md](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/TECHNICAL_EXPLANATION.md)
- [docs/CONFIG_AND_DEPLOY_GUIDE.md](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/docs/CONFIG_AND_DEPLOY_GUIDE.md)
- [docs/pitch_deck_draft.md](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/docs/pitch_deck_draft.md)
- [docs/JUDGE_DEMO_RUNBOOK.md](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/docs/JUDGE_DEMO_RUNBOOK.md)
