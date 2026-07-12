# JUDGE DEMO RUNBOOK - P3 GUARDIAN PRICING INTELLIGENCE

Tai lieu nay dung cho phien demo 5 phut. Muc tieu la chung minh tung outcome trong `P3.pdf` bang UI va API dang chay, khong noi qua pham vi MVP.

## 1. Preflight truoc khi demo

```powershell
# Terminal 1
cd backend
..\.venv312\Scripts\python.exe -m pytest -q
..\.venv312\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# Terminal 2
cd frontend
npm.cmd run build
npm.cmd run dev -- --host 127.0.0.1 --port 3000
```

Kiem tra nhanh:

- backend: `http://127.0.0.1:8001/`
- Swagger: `http://127.0.0.1:8001/docs`
- frontend: `http://127.0.0.1:3000/`
- Langfuse runtime URL: `GET /api/v1/agent/runtime-status`

Neu database chua dung demo state, vao `Guardrails` va bam `Reload demo dataset`.

## 2. Demo flow 5 phut

### 0:00 - 0:30: Dat bai toan

Noi ngan:

> Gia niem yet khong phai gia that. Commercial team can biet effective price sau discount, voucher, bundle va flash sale tren tat ca kenh, nhung van phai bao ve margin.

### 0:30 - 1:30: Pricing Command

Chi vao bon KPI:

- `200/200` target SKU
- omnichannel CPI, voi `100` la parity
- automated observation coverage
- fresh observation trong SLA 24 gio

Sau do show:

- valid observation rate
- promotion signal count
- pricing opportunity count
- latest signal age

Thong diep:

> Day la single operational view, khong phai trung binh gia VND giua cac category. CPI duoc tinh tren price-relative cua tung SKU.

### 1:30 - 2:20: Channel CPI va promotion intelligence

Tai chart `Competitor pricing index by channel`:

- line `100` la parity
- CPI > 100: Guardian premium so voi kenh
- CPI < 100: Guardian value so voi kenh
- moi channel co coverage rieng

Tai `Promotion intelligence`:

- show voucher count
- show bundle count
- show flash sale count
- show so pricing gaps can xu ly

### 2:20 - 3:00: SKU Insights

Chon mot SKU co CPI lech nhieu:

- show Guardian price va cost
- show latest effective price cua tung channel
- show raw price, discount, voucher, promo va net price
- show noise filter cho anomaly va inventory advantage cho OOS
- show 7-day history

### 3:00 - 4:15: Agent decision

Tai `Decision Desk`:

1. bam `Run pricing agent` voi refresh data tat neu mang thi bi gioi han
2. show decision audit trail
3. mo mot action
4. giai thich margin current, margin after action, threshold va market reference
5. mo Langfuse trace de show span -> tool -> decision summary

Thong diep:

> Agent khong tu y sua gia. No chon market reference sach, tinh margin theo rule va dua action vao human approval.

### 4:15 - 5:00: Human approval va ket qua

Approve mot price action:

- Guardian price duoc cap nhat
- CPI duoc tinh lai ngay
- alert cu duoc resolve
- action co audit status `Approved`

Ket:

> MVP rut gon mot vong theo doi -> phan tich -> de xuat -> phe duyet thanh mot workflow co the chay hang ngay.

## 3. Bang chung ky thuat nen nho

```text
Products:                    200
Competitor channels:         6
7-day price observations:    8,400
Competitor links:            1,200
Daily scheduler interval:    86,400 seconds
Backend tests:               12
```

Endpoint quan trong:

- `GET /api/v1/pricing/channel-index`
- `GET /api/v1/pricing/cpi-index`
- `GET /api/v1/agent/briefing`
- `GET /api/v1/agent/runtime-status`
- `POST /api/v1/agent/run`
- `POST /api/v1/agent/actions/{id}/approve`

## 4. Cach tra loi cau hoi kho

### Day co phai real-time khong?

Tra loi:

> P3 cho phep real-time hoac daily point-in-time. MVP dang dung daily autonomous scheduler va co nut refresh on-demand. Day khong phai streaming tick-by-tick.

### Co that su giam hon 90% manual effort khong?

Tra loi:

> MVP chung minh automated observation coverage tren pipeline. Muc giam manual effort hon 90% can duoc do bang pilot voi commercial team; chung toi khong bien proxy ky thuat thanh ket qua business chua duoc do.

### Data nao la that, data nao la fallback?

Tra loi:

> Apify/Playwright/Crawl4AI la connector that. Khi bi chan mang, fixture fallback giu demo E2E. UI va database van normalize cung mot schema; production se gan provenance va SLA cho tung source.

### Tai sao khong dung RAG/LLM de dat gia?

Tra loi:

> De bai khong cung cap pricing policy de retrieval, va pricing la quyet dinh margin nhay cam. MVP dung deterministic rule/template de audit duoc. LangGraph van dieu phoi agent state va tools; Langfuse trace toan bo decision workflow.

### Co tu dong sua gia khong?

Tra loi:

> Khong. Agent tao pending action. Commercial operator approve hoac reject; moi approval deu co audit trail va CPI duoc tinh lai.

## 5. Failure fallback

Neu outbound scrape bi chan:

- khong bam refresh 200 SKU trong luc demo
- dung demo seed da co 7-day history
- run agent voi `refresh_market_data=false`
- noi ro fallback la resilience path, khong phai gia live

Neu Langfuse cham:

- show decision audit trail va `decision_summary` trong UI
- show `last_trace_id` / `last_trace_url` tu runtime-status
- khong de tracing cloud chan core pricing workflow

Neu frontend co van de:

- dung Swagger tai `/docs`
- goi `channel-index`, `briefing`, `agent/run` va `approve` theo thu tu

## 6. Khong nen noi

- khong noi scraper da production-grade cho 200 SKU
- khong noi automation coverage bang manual effort reduction da do
- khong noi fixture la live market data
- khong noi agent hien chain-of-thought; UI chi hien decision audit trail co cau truc
- khong cam ket auto-price khong can con nguoi
