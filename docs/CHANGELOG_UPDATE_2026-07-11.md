# Changelog Update - 2026-07-11

Tai lieu nay ghi lai lan toi uu hoa cuoi cho Agent Workspace va runtime observability cua Guardian Pricing OS.

## 1. Live agent observability

`GET /api/v1/agent/runtime-status` hien tra them snapshot audit-safe cua run dang chay:

- agent dang active
- phase hien tai
- rationale ngan gon dang duoc hien thi cho nguoi dung
- tool dang chay va trang thai tool
- SKU dang duoc xu ly
- tien do so san pham
- 8 tool events gan nhat
- execution timeline toi da 40 activity events
- roster va trang thai cua ca 4 agent

Snapshot duoc luu tai `backend/app/agents/shared/runtime_support.py` trong bo nho cua process hien tai. Day la live observability cho hackathon, khong phai kho luu lich su phan tan.

## 2. Market Observer da tro thanh stage agent co runtime that

Da them `run_market_observer_cycle()` tai `backend/app/agents/market_observer/market_observer_agent.py`.

Market Observer hien co hai nhanh ro rang:

1. `refresh_competitor_market`: quet cac san pham, goi link discovery/scraper, chuan hoa va ghi snapshot gia.
2. `load_latest_market_signals`: tai lai tin hieu da luu khi run khong yeu cau live refresh.

Scraper co callback tien do theo tung san pham, nen Agent Workspace co the hien SKU dang duoc quan sat thay vi chi hien mot dong "scraping" chung chung.

## 3. Timeline va roster tren giao dien

`frontend/src/pages/AgentWorkspace.jsx` hien hien:

- active agent, phase, current tool va progress
- current reasoning summary theo huong audit-safe
- current SKU
- danh sach 4 agent: Orchestrator, Market Observer, Margin Guardian, Supplier Negotiator
- tool history gan nhat
- execution timeline voi agent, phase, trang thai va timestamp

UI polling runtime moi 1 giay; du lieu quyet dinh va action queue van refresh theo chu ky 3 giay.

Khong hien chain-of-thought bi mat. Giao dien chi hien rationale co the kiem tra tu du lieu, margin floor, price gap va action duoc tao.

## 4. Xu ly loi va tinh trung thuc cua trang thai

- Tool khong co Langfuse van ghi nhan success/error event nhu nhau.
- Tool loi duoc hien thi trong live runtime thay vi im lang.
- Neu orchestration tra task `Failed` ma khong nem exception, runtime van danh dau run loi dung theo status task.
- Scheduler va manual trigger van dung agent lock de tranh hai run pricing chay trung nhau.

## 5. Kiem thu da thuc hien

- Python compile cho cac module agent, scraper va runtime: pass.
- Backend test suite: `16 passed` trong `.venv312`.
- Market Observer smoke test: 200 products, 200 stored signal sets, tool event va activity timeline duoc tao.
- Full decision cycle voi refresh tat: `Completed`; da ghi nhan day du tool cua Market Observer, Margin Guardian va Supplier Negotiator.
- Frontend production build: pass voi Vite.
- `git diff --check`: khong co whitespace error; cac dong canh bao con lai chi la quy uoc CRLF cua Windows.

Ngoai ra da sua loi khoi dong FastAPI tren version moi: doi `GzipMiddleware` thanh `GZipMiddleware` trong `backend/app/main.py`.

## 7. Them data quality va confidence theo SKU

Da them `backend/app/services/data_quality.py` de cham diem bang chung cho moi SKU theo 4 thanh phan:

- coverage channel: 35%
- valid observations: 30%
- freshness SLA: 25%
- competitor link coverage: 10%

Ket qua duoc tra trong briefing voi `data_quality_pct`, `confidence_label` va `data_quality_reasons`, sau do hien truc tiep tren Overview va Agent Workspace.

## 8. Them business KPI scorecard

Da them `backend/app/services/business_kpis.py` va endpoint `GET /api/v1/agent/kpis`.

Overview hien hien:

- Decision confidence
- Estimated margin exposure under review
- Estimated protected exposure routed to negotiation
- Recommendation adoption
- Decision coverage va evidence readiness qua API

Metric exposure duoc danh dau la estimated, khong nhan la realized savings neu chua co human approval va execution.

## 9. Hop nhat tai lieu Markdown

Da tao tai lieu tong hop chinh thuc:

- `docs/CODEBASE_DOCUMENTATION.md`

Tai lieu nay gom lai architecture, agent runtime, end-to-end workflow, data quality, KPI, observability, deployment, demo narrative va production risks; cac tai lieu chi tiet cu van duoc giu lai va duoc lien ket o cuoi file.

## 6. Gioi han con lai can noi trung thuc

- Live snapshot la in-process memory; khi chay nhieu worker/process can Redis hoac event bus de dong bo.
- Scheduler hien la background thread trong process FastAPI; production nen chuyen sang worker queue/Celery/Temporal.
- Scraper production cho 200 SKU van can rate limit, retry policy, monitoring va connector rieng theo tung marketplace.
- Langfuse la observability layer; khong thay the audit database cho lich su pricing dai han.
