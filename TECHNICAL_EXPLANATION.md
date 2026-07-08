# TECHNICAL EXPLANATION

Tai lieu nay tap trung vao workflow thuc te cua codebase hien tai, khong theo boilerplate cu.

## 1. Workflow overview

Du an co 4 luong chinh:

1. Seed demo dataset
2. Scrape / refresh du lieu gia doi thu
3. Tinh CPI va tao alerts
4. Chay AI agent va human approval

## 2. Architecture workflow

```mermaid
flowchart TD
    User[Category Manager]
    FE[React Frontend]
    API[FastAPI Backend]
    DB[(SQLite guardian.db)]

    subgraph DemoData
        SKU[data/sku_master.csv]
        COMP[data/competitor_mock.csv]
        SAMPLE[dataset_shopee-scraper_*.json]
    end

    subgraph Services
        Seed[demo_seed.py]
        Scraper[scraper_engine.py]
        CPI[cpi_calculator.py]
        Agent[agent_engine.py]
        Evidence[scraped_samples.py]
    end

    User --> FE
    FE --> API
    API --> DB

    SKU --> Seed
    COMP --> Seed
    Seed --> DB

    API --> Scraper
    Scraper --> DB
    DB --> CPI
    CPI --> DB
    DB --> Agent
    Agent --> DB

    SAMPLE --> Evidence
    Evidence --> API
    API --> FE
```

## 3. Seed workflow

Workflow nay dung khi muon reset demo nhanh truoc luc thuyet trinh.

```mermaid
sequenceDiagram
    autonumber
    participant FE as Configuration page
    participant API as products.py
    participant Seed as demo_seed.py
    participant DB as SQLite
    participant CPI as cpi_calculator.py

    FE->>API: POST /api/v1/products/seed-demo
    API->>Seed: seed_demo_dataset(db)
    Seed->>DB: Delete Product / CompetitorPrice / Alert / Agent data
    Seed->>DB: Insert products from sku_master.csv
    Seed->>DB: Insert competitor prices from competitor_mock.csv
    Seed->>CPI: calculate_all_cpi(db)
    CPI->>DB: Create PricingIndex + Alerts
    API-->>FE: status + counts
```

## 4. Scrape workflow

Workflow nay dung khi user bam "Scan channels".

```mermaid
sequenceDiagram
    autonumber
    participant FE as Overview
    participant API as scraper.py
    participant SE as scraper_engine.py
    participant DB as SQLite
    participant CPI as cpi_calculator.py

    FE->>API: POST /api/v1/scraper/trigger
    API->>SE: run_scraper_for_all_products()
    loop Moi product
        SE->>SE: scrape_via_apify / crawl4ai / playwright
        alt No live source or scrape fail
            SE->>SE: simulate_competitor_price()
        end
        SE->>SE: check_price_anomaly()
        SE->>DB: Save CompetitorPrice
        SE->>CPI: calculate_cpi_for_product()
        CPI->>DB: Update PricingIndex
        CPI->>DB: Generate alerts
    end
```

## 5. CPI and alert workflow

Day la logic de bien du lieu gia thanh decision signal.

```mermaid
flowchart LR
    CP[Latest competitor prices]
    Filter[Bo qua OOS / null / suspicious]
    Avg[Average competitor net price]
    CPIVal[Competitor Pricing Index]
    Rec[Recommendation]
    Alert[Generate alerts]

    CP --> Filter
    Filter --> Avg
    Avg --> CPIVal
    CPIVal --> Rec
    CPIVal --> Alert
```

Chi tiet:

- `CPI = guardian_price / average_competitor_price * 100`
- Neu CPI cao hon threshold -> `Lower Price`
- Neu CPI thap hon threshold -> `Increase Price`
- Neu competitor undercut manh -> tao `High` hoac `Medium` alert

## 6. Agent workflow

Day la workflow quan trong nhat cho theme agentic AI.

```mermaid
sequenceDiagram
    autonumber
    participant FE as AgentWorkspace
    participant API as agent.py
    participant DB as SQLite
    participant Agent as agent_engine.py
    participant Config as config.json
    participant RAG as supplier_policies.txt / RAG

    FE->>API: POST /api/v1/agent/run
    API->>DB: Create AgentTask
    API->>Agent: run_agentic_optimization_loop()
    Agent->>DB: Load unresolved alerts

    loop Moi alert
        Agent->>Agent: margin_analysis
        Agent->>Config: Read min_margin + custom instruction
        Agent->>Agent: determine_strategy
        alt strategy = match
            Agent->>DB: Create AUTO_PRICE_MATCH (Pending)
        else strategy = negotiate
            Agent->>RAG: Query supplier policy context
            Agent->>DB: Create SUPPLIER_EMAIL_DRAFT (Executed)
        end
        Agent->>DB: Append logs to AgentTask
    end

    FE->>API: GET /api/v1/agent/tasks
    FE->>API: GET /api/v1/agent/actions
    API-->>FE: Logs + actions
```

## 7. Agent briefing workflow

Frontend mission control khong ghep du lieu thu cong nua. No dung `GET /agent/briefing`.

```mermaid
flowchart LR
    Alerts[Unresolved alerts]
    Prices[Latest valid competitor prices]
    Margin[Margin analysis]
    Queue[Priority queue]
    Summary[Briefing summary]
    FE[Overview page]

    Alerts --> Margin
    Prices --> Margin
    Margin --> Queue
    Margin --> Summary
    Queue --> FE
    Summary --> FE
```

`build_alert_decision_context()` la ham trung tam o workflow nay.

No tra ra:

- product nao bi undercut
- competitor nao lien quan
- gap gia bao nhieu
- margin neu match
- recommendation `match` hay `negotiate`
- rationale de frontend hien thi

## 8. Human approval workflow

```mermaid
sequenceDiagram
    autonumber
    participant CM as Category Manager
    participant FE as AgentWorkspace
    participant API as agent.py
    participant DB as SQLite

    CM->>FE: Approve AUTO_PRICE_MATCH
    FE->>API: POST /api/v1/agent/actions/{id}/approve
    API->>DB: Mark action Approved
    API->>DB: Update guardian_price on Product
    API->>DB: Resolve unresolved alerts for same product
    API-->>FE: success

    alt Reject action
        CM->>FE: Reject
        FE->>API: POST /api/v1/agent/actions/{id}/reject
        API->>DB: Mark action Rejected
        API->>DB: Resolve unresolved alerts
        API-->>FE: success
    end
```

## 9. Branch `branch_of_Duy` workflow

Du lieu tu branch nay hien duoc dung nhu scrape evidence, khong phai full ingestion pipeline.

```mermaid
flowchart LR
    JSON[dataset_shopee-scraper_*.json]
    Service[scraped_samples.py]
    Match[Lightweight catalog matching]
    API[scraper/branch-samples]
    UI[Overview]

    JSON --> Service
    Service --> Match
    Match --> API
    API --> UI
```

Muc dich:

- show bang chung scrape sample that
- map sample listing voi catalog hien tai neu co the
- tang do thuyet phuc cho pitch

## 10. Workflow de demo tren san khau

Thu tu nen dung:

1. Seed demo dataset
2. Mo Overview
3. Giai thich KPI, priority queue, branch sample evidence
4. Mo ProductInsights de show raw pricing detail
5. Chay agent trong AgentWorkspace
6. Approve 1 action
7. Quay lai Overview de cho thay state da thay doi

## 11. Ghi chu ky thuat

- Agent hien tai co the chay rule-based fallback neu khong co OpenAI key
- Scraper hien tai co the fallback sang simulated pricing
- Dashboard da duoc toi uu cho demo mission-control
- Frontend build trong moi truong nay van bi vuong issue Vite/esbuild voi protected parent directories
