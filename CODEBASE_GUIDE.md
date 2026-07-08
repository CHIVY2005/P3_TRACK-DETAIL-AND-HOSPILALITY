# CODEBASE GUIDE

Tai lieu nay giai thich toan bo codebase cua du an GUARDIAN theo dung trang thai hien tai. Muc tieu la de:

- onboarding nhanh cho teammate
- hieu duoc luong du lieu va luong suy luan cua agent
- biet file nao quan trong khi can sua de demo hoac mo rong

## 1. Muc tieu san pham

GUARDIAN la mot pricing intelligence dashboard cho Guardian. Thay vi chi hien thi analytics, no co them mot agent de:

1. Phat hien san pham dang co van de gia
2. Ly giai xem co nen match gia hay khong
3. Tao hanh dong cho con nguoi duyet

Vay nen codebase co 3 lop lon:

- data va pricing engine
- agent reasoning layer
- dashboard va approval UI

## 2. Thu muc goc

```text
backend/                  FastAPI app
frontend/                 React app
scripts/                  script tao mock data va test nhanh
data/                     CSV du lieu demo
docs/                     de bai, pitch draft, preview
dataset_shopee-*.json     scrape sample tu branch_of_Duy
README.md                 huong dan su dung
TECHNICAL_EXPLANATION.md  tai lieu cu giai thich ky thuat
CODEBASE_GUIDE.md         tai lieu nay
```

## 3. Backend

Backend nam trong `backend/app/`.

### 3.1 `main.py`

File [backend/app/main.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/main.py) la entrypoint cua FastAPI.

No lam 4 viec:

- khoi tao app
- bat CORS
- auto create database tables
- dang ky routers cho `products`, `pricing`, `alerts`, `scraper`, `agent`

### 3.2 `config.py`

File [backend/app/config.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/config.py) chua:

- bien moi truong
- cau hinh SQLite/Postgres
- default thresholds
- doc va ghi `backend/data/config.json`

Phan quan trong o day la `get_agent_config()` va `save_agent_config()`. Frontend trang Configuration goi vao 2 ham nay qua API.

### 3.3 Database layer

#### `db/session.py`

File [backend/app/db/session.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/db/session.py):

- tao `engine`
- tao `SessionLocal`
- expose dependency `get_db()`

#### `db/models.py`

File [backend/app/db/models.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/db/models.py) la trung tam du lieu.

Bang chinh:

- `Product`
  - SKU cua Guardian
  - co `barcode`, `name`, `category`, `guardian_price`, `cost_price`

- `CompetitorPrice`
  - 1 lan ghi nhan gia doi thu
  - co `raw_price`, `discount`, `net_price`, `stock_status`, `is_suspicious`

- `PricingIndex`
  - CPI cua 1 product
  - co `competitor_index`, `average_competitor_price`, `recommendation`

- `Alert`
  - canh bao khi Guardian overpriced, underpriced, hoac bi undercut

- `AgentTask`
  - 1 lan chay agent
  - chua `objective`, `status`, `logs`

- `AgentAction`
  - hanh dong agent tao ra
  - vi du `AUTO_PRICE_MATCH`, `SUPPLIER_EMAIL_DRAFT`

Neu muon demo hay them logic moi, day la noi dau tien can hieu.

### 3.4 Pydantic schemas

File [backend/app/schemas.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/schemas.py) map model DB ra API response.

Phan moi quan trong:

- `AgentBriefingSummary`
- `AgentBriefingChannel`
- `AgentBriefingPriority`
- `AgentBriefing`
- `ScrapeSample`

Nhung schema nay phuc vu cho trang mission control moi.

## 4. Backend routes

### 4.1 `routes/products.py`

File [backend/app/routes/products.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/products.py) xu ly:

- CRUD product
- import CSV
- seed demo dataset bang `POST /products/seed-demo`

Day la noi de reset data nhanh truoc khi demo.

Route moi quan trong:

- `POST /api/v1/products/seed-demo`

Route nay goi service `seed_demo_dataset()` de nap:

- `data/sku_master.csv`
- `data/competitor_mock.csv`

va sau do tinh lai CPI va alerts.

### 4.2 `routes/pricing.py`

File [backend/app/routes/pricing.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/pricing.py) expose dashboard data:

- `GET /pricing/overview`
- `GET /pricing/cpi-index`

`overview` dung cho KPI tong quan.

`cpi-index` dung cho list SKU trong trang Product Insights.

### 4.3 `routes/alerts.py`

File [backend/app/routes/alerts.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/alerts.py):

- list alerts
- resolve alert

Trang Overview va Product UI deu dung endpoint nay.

### 4.4 `routes/scraper.py`

File [backend/app/routes/scraper.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/scraper.py):

- `POST /scraper/trigger`
- `GET /scraper/status`
- `GET /scraper/branch-samples`

`branch-samples` la route moi de doc evidence tu `branch_of_Duy`.

### 4.5 `routes/agent.py`

File [backend/app/routes/agent.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/routes/agent.py) la route quan trong nhat cho theme agentic AI.

Nhiem vu:

- chay agent background
- expose task history
- expose action history
- expose `agent/briefing`
- approve / reject action
- doc / ghi config

`GET /agent/briefing` la endpoint moi tong hop:

- active alerts
- priority queue
- channel summary
- latest task
- pending action count

Nghia la frontend khong can tu ghep du lieu tu 5 endpoint nua.

## 5. Backend services

### 5.1 `services/cpi_calculator.py`

File [backend/app/services/cpi_calculator.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/cpi_calculator.py) chua pricing logic cot loi.

Ham quan trong:

- `calculate_cpi_for_product()`
  - lay gia doi thu moi nhat cua tung channel
  - bo qua `OUT_OF_STOCK`, `net_price = None`, va `is_suspicious = True`
  - tinh average competitor price
  - tinh CPI
  - dua ra recommendation

- `generate_alerts_for_product()`
  - tao alert theo threshold
  - tao alert severity cao khi doi thu undercut manh

- `check_price_anomaly()`
  - so gia moi voi lich su 10 lan scrape sach gan nhat
  - neu lech qua 50% thi danh dau suspicious

Ham nay giai quyet mot diem pitch quan trong: du lieu scrape khong duoc tin mu quang.

### 5.2 `services/agent_engine.py`

File [backend/app/services/agent_engine.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/agent_engine.py) la trai tim cua agent.

No co 2 tang:

#### Tang 1: helper cho dashboard

- `build_alert_decision_context()`

Ham nay lay 1 alert va bien no thanh 1 object de frontend hieu duoc:

- product nao dang gap van de
- competitor nao dang re hon
- neu match thi margin con bao nhieu
- nen `match` hay `negotiate`
- ly do bang text

Day la logic dung cho `GET /agent/briefing`.

#### Tang 2: autonomous loop

- `run_agentic_optimization_loop()`
- `run_langgraph_agent_for_alert()`
- `node_run_margin_analysis()`
- `node_determine_strategy()`
- `node_apply_auto_match()`
- `node_draft_supplier_negotiation()`

Ngoai ra, agent bay gio co mot tool layer ro rang:

- `tool_compute_margin_scenarios()`
- `tool_propose_price_match()`
- `tool_lookup_supplier_policy()`
- `tool_generate_supplier_email()`

Tat ca deu duoc chay qua `_run_agent_tool()`. Ham nay co 3 vai tro:

- ghi log tool call vao `AgentTask.logs`
- gom tool event thanh cau truc co ten / input / output / status
- tu dong tao Langfuse tool observation neu credentials hop le

Luong suy nghi:

1. Lay tat ca unresolved alerts
2. Chay qua tung alert
3. Phan tich margin
4. Xac dinh strategy
5. Tao `AgentAction`
6. Ghi log vao `AgentTask`

Neu co OpenAI key thi no co the goi LLM. Neu khong, no fallback sang rule-based logic.

Neu co Langfuse key that thi:

- ca root agent run duoc trace
- moi alert run duoc trace thanh child span
- moi tool call duoc trace thanh observation type `tool`
- LLM strategy call duoc gan Langfuse callback qua LangChain

### 5.3 `services/demo_seed.py`

File [backend/app/services/demo_seed.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/demo_seed.py) moi duoc them de phuc vu demo.

No:

- clear du lieu cu
- doc 2 file CSV trong `data/`
- insert lai Product va CompetitorPrice
- tinh toan CPI va alerts

Rat huu ich truoc khi presentation, vi reset chi bang 1 API call.

### 5.4 `services/scraped_samples.py`

File [backend/app/services/scraped_samples.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/services/scraped_samples.py) doc 2 file scrape sample tu `branch_of_Duy`.

No lam 3 viec:

- mo file JSON scrape
- chuan hoa truong title / price / discount / url
- thu match item scrape voi product catalog bang token overlap rat nhe

No khong phai matching engine production. No la lop "evidence adapter" de dashboard show duoc:

- branch nay co scrape that
- listing nao lien quan den catalog hien tai

## 6. Scraper layer

### 6.1 `scraper/scraper_engine.py`

File [backend/app/scraper/scraper_engine.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/app/scraper/scraper_engine.py) chua rat nhieu che do scrape:

- `scrape_via_apify()` cho Shopee / Lazada
- `scrape_via_crawl4ai()` cho web nhu Pharmacity / GrabMart
- `scrape_via_playwright()` cho Hasaki / TikTok Shop
- `simulate_competitor_price()` de fallback khi khong co key

Flow thuc te:

1. tim product theo `product_id`
2. thu scrape tung competitor theo plugin / channel phu hop
3. neu that bai thi simulate
4. check anomaly
5. save vao `CompetitorPrice`
6. recalculate CPI

### 6.2 `scraper/mock_scraper.py`

File nay la version gia lap cu hon. Co the xem nhu reference hoac fallback.

## 7. Frontend

### 7.1 `src/App.jsx`

File [frontend/src/App.jsx](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/App.jsx):

- giu `activeTab`
- poll scraper status
- poll agent task va alert count
- render 4 man:
  - Overview
  - ProductInsights
  - AgentWorkspace
  - Configuration

No dong vai tro shell cua toan bo app.

### 7.2 `src/pages/Overview.jsx`

File [frontend/src/pages/Overview.jsx](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/pages/Overview.jsx) da duoc doi huong manh sang hackathon demo.

No fetch:

- `pricing/overview`
- `alerts`
- `agent/briefing`
- `agent/actions`
- `scraper/branch-samples`

No hien thi:

- mission band
- KPI
- live reasoning trace
- priority queue
- channel pricing map
- branch scrape evidence
- alert feed
- recent agent actions

Neu ban chi co 2 phut demo, day la man hinh nen chieu dau tien.

### 7.3 `src/pages/ProductInsights.jsx`

File [frontend/src/pages/ProductInsights.jsx](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/pages/ProductInsights.jsx) dung de drill-down theo SKU.

Chuc nang:

- tim SKU
- chon SKU
- xem image, category, barcode
- xem bang net price cua tung competitor
- xem chart 7 ngay

No la man "chung minh bo du lieu khong chi la KPI top-level".

### 7.4 `src/pages/AgentWorkspace.jsx`

File [frontend/src/pages/AgentWorkspace.jsx](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/pages/AgentWorkspace.jsx):

- trigger `POST /agent/run`
- poll task dang chay
- hien terminal style logs
- hien danh sach actions
- approve / reject price match
- xem supplier email draft

Day la man "agent operator console".

### 7.5 `src/pages/Configuration.jsx`

File [frontend/src/pages/Configuration.jsx](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/pages/Configuration.jsx):

- doc / ghi `agent/config`
- upload CSV
- seed lai demo dataset

Button reset hien tai da duoc sua de goi `POST /products/seed-demo`, khong con goi scraper trigger nhu truoc.

### 7.6 `src/index.css`

File [frontend/src/index.css](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend/src/index.css) la lop style lon nhat.

No chua:

- palette mau
- glass cards
- sidebar
- terminal styles
- dashboard layouts
- mission control components moi

Neu can sua giao dien nhanh truoc demo, day la file can cham vao.

## 8. Du lieu va tai nguyen demo

### 8.1 `data/sku_master.csv`

Master data cho product catalog demo.

### 8.2 `data/competitor_mock.csv`

Lich su gia competitor demo.

### 8.3 `scripts/generate_mock_data.py`

File [scripts/generate_mock_data.py](/C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/scripts/generate_mock_data.py) tao 200 SKU va 8400 competitor records.

No:

- random brand / category / volume
- random gia Guardian
- random factor theo tung competitor
- random voucher / promo
- random OOS
- random suspicious cases

Nghia la data demo kha phong phu cho hackathon.

### 8.4 `dataset_shopee-scraper_*.json`

Day la scrape sample tu `branch_of_Duy`.

- `...05-01-14-978.json` co 1 listing that
- `...04-32-31-501.json` la sample mock cua actor

No duoc dung de lam bang chung cho huong scrape that trong mission control.

## 9. Luong du lieu end-to-end

### Luong 1: seed demo

1. Frontend goi `POST /products/seed-demo`
2. Backend clear DB
3. Backend doc CSV
4. Backend insert Product + CompetitorPrice
5. Backend tinh CPI + tao alerts
6. Frontend refresh dashboard

### Luong 2: scrape / refresh gia

1. Frontend goi `POST /scraper/trigger`
2. Backend chay scraper background
3. Từng product duoc ghi them competitor prices
4. CPI va alerts duoc cap nhat

### Luong 3: chay agent

1. Frontend goi `POST /agent/run`
2. Backend tao `AgentTask`
3. Agent tu refresh competitor prices truoc
4. CPI va alerts duoc cap nhat tu du lieu moi
5. Agent lay unresolved alerts
6. Agent phan tich margin
7. Agent quyet dinh `match` hoac `negotiate`
8. Agent tao `AgentAction`
9. Frontend poll va hien logs

### Luong 4: approve action

1. User bam approve
2. Frontend goi `POST /agent/actions/{id}/approve`
3. Backend cap nhat `guardian_price`
4. Backend resolve alerts lien quan

## 10. Cac file can sua theo tung nhu cau

Neu muon...

- doi logic CPI: sua `backend/app/services/cpi_calculator.py`
- doi logic agent: sua `backend/app/services/agent_engine.py`
- doi reset data demo: sua `backend/app/services/demo_seed.py`
- doi evidence scrape sample: sua `backend/app/services/scraped_samples.py`
- doi dashboard tong quan: sua `frontend/src/pages/Overview.jsx`
- doi man agent terminal: sua `frontend/src/pages/AgentWorkspace.jsx`
- doi giao dien toan cuc: sua `frontend/src/index.css`

## 11. Diem manh va gioi han

### Diem manh

- Demo duoc ngay, khong can phu thuoc full infra
- Co agent flow ro rang
- Co human approval
- Co data history
- Co branch scrape evidence that

### Gioi han

- Chua co queue worker that
- Chua co production-grade matching catalog
- Chua co auth
- Frontend build trong moi truong hien tai van co van de Vite/esbuild do parent directory permissions

## 12. Thu tu nen demo

Thu tu de pitch on nhat:

1. Seed demo dataset
2. Mo Overview
3. Noi ve mission control va branch evidence
4. Chuyen sang Product Insights de show raw pricing detail
5. Quay lai Agent Workspace, bam run agent
6. Approve 1 action
7. Ket bang Configuration de cho thay threshold co the dieu chinh

## 13. Ket luan

Codebase nay khong con la boilerplate rong nua. No da co:

- pricing engine
- alert engine
- agent reasoning loop
- approval workflow
- branch scrape evidence
- demo data path on dinh

Neu can day tiep sau hackathon, huong dung nhat la:

- thay sample scrape bang pipeline scrape that
- nang cap matching giua listing scrape va catalog noi bo
- dua background jobs ra worker queue
- bo sung auth va audit log
