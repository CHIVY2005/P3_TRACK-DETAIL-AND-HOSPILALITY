# TOP 5 COMPETITION STRATEGY - GUARDIAN PRICING OS

Muc tieu khong phai co nhieu feature nhat. Muc tieu la de giam khao nho ro mot san pham, tin duoc no chay, va thay duoc mot quyet dinh business duoc khép kin tu signal den action.

## 1. Dinh vi mot cau

> Guardian Pricing OS bien gia doi thu sau voucher, bundle va flash sale thanh quyet dinh gia bao ve margin, co phe duyet va co audit trail trong cung mot daily loop.

Khong pitch day la `scraper`, `dashboard` hay `AI chatbot`. Ba cach goi do deu lam giam gia tri business.

## 2. Mat bang 4 de bai

### P1 - Product onboarding

Kieu bai pho bien:

- upload PDF/image
- OCR va extract field
- checklist missing document
- claim compliance classifier

Rui ro cua doi thu:

- demo giong document chatbot
- compliance accuracy kho chung minh khi policy data han che
- kho show business action sau khi flag

### P2 - Voice of Customer

Kieu bai pho bien:

- ingest review
- sentiment/topic dashboard
- summary va alert
- competitor benchmark

Rui ro cua doi thu:

- sentiment dashboard rat de trung y tuong
- insight co the chung chung
- kho chung minh root cause va corrective action

### P3 - Pricing intelligence

Co hoi khac biet:

- data thay doi lien tuc va co business urgency ro
- effective price phuc tap hon listed price
- CPI, margin va approval co the tinh va kiem chung
- co action that sau insight
- demo duoc closed loop trong 5 phut

### P4 - Demand forecasting

Kieu bai pho bien:

- upload Excel
- forecast occupancy/ADR/RevPAR
- anomaly va rate recommendation

Rui ro cua doi thu:

- forecast quality can backtest va du lich su du dai
- recommendation de bi xem la dashboard cong bieu do
- sample data co the khong du de chung minh generalization

## 3. Nam tru cot de vao top 5

### 1. Single source of truth co data quality

Phai show:

- 200/200 priority SKU
- 6 channels
- latest clean observation theo `SKU + channel`
- OOS va anomaly bi loai khoi CPI
- freshness va valid observation rate

### 2. Effective price intelligence

Phai show tren mot SKU:

- raw price
- direct discount
- voucher impact
- bundle / flash-sale mechanics
- final net price
- source link

Day la diem de phan biet voi scraper chi lay mot con so gia.

### 3. Decision, khong chi dashboard

Phai show:

- pricing gap
- current margin
- margin if aligned
- rule threshold
- `align` hoac `negotiate`
- pending action

### 4. Trust va control

Phai show:

- operator approve / reject
- duplicate action guardrail
- CPI recalculate sau approval
- Langfuse trace va decision summary
- rule-based pricing, khong dung LLM de tu dat gia

### 5. Demo resilience

Phai noi ro:

- connector that: Apify / Playwright / Crawl4AI
- fallback chi la resilience path
- daily point-in-time dap ung brief
- core decision loop van chay khi outbound bi chan

## 4. First viewport phai tra loi duoc gi

Trong 10 giay dau, giam khao phai doc duoc:

- day la Guardian
- day la pricing operating system
- dang theo doi bao nhieu SKU va channel
- data co tu dong va con moi khong
- CPI hien tai lech parity the nao

Visual system:

- Guardian yellow: brand, active navigation, primary command, parity
- charcoal: operation shell va authority
- red: risk / premium gap
- green: value / safe outcome
- blue: neutral information va trace

Khong dung gradient trang tri, marketing hero hay card long card.

## 5. Demo 5 phut de tao wow moment

### 0:00 - 0:35

Noi problem bang effective price:

> Mot SKU co the co listed price, voucher, combo va flash sale khac nhau tren 6 kenh. Commercial team khong the ra quyet dinh tu listed price.

### 0:35 - 1:25

Show Pricing Command:

- 200/200
- 6 channels
- automation coverage
- freshness 24h
- channel CPI va promotion counts

### 1:25 - 2:15

Mo SKU Insights:

- raw -> discount -> voucher -> net
- source URL
- anomaly/OOS
- 7-day trend

### 2:15 - 3:30

Mo Decision Desk:

- competitor reference
- margin before/after
- decision evidence
- Langfuse tool spans

### 3:30 - 4:25

Approve mot action:

- price thay doi
- CPI duoc tinh lai
- alert duoc cap nhat
- action status thanh Approved

### 4:25 - 5:00

Ket bang business outcome:

> He thong tu dong hoa viec quan sat va tinh toan; con nguoi giu quyen quyet dinh. Commercial team bat dau buoi sang bang action queue, khong bat dau bang spreadsheet.

## 6. Bang chung giam khao co the kiem tra

| Claim | Evidence |
|---|---|
| Top 200 SKU | `channel-index.summary.monitored_sku` |
| 6 channel | channel index va promotion intelligence |
| Daily visibility | freshness SLA 24h va scheduler 86.400 giay |
| Effective price | SKU net-price table va mapper test |
| Margin protection | Decision Desk va margin scenarios |
| Human control | pending action, approve/reject API |
| Explainability | decision summary va Langfuse trace URL |
| Fresh clone ready | startup bootstrap 200 / 8.400 / 1.200 |
| Reliability | 12 backend tests va production frontend build |

## 7. Khong duoc noi qua

- khong noi 70-90% manual effort reduction da duoc do neu chua pilot
- khong goi fixture la live data
- khong noi scraper production-grade cho 200 SKU
- khong goi audit log la chain-of-thought
- khong noi action duoc auto-execute khi van can approval
- khong dua RAG/LLM vao pricing chi de nghe co ve AI

## 8. Viec co tac dong lon nhat sau MVP

1. ghi source provenance cho tung observation: live / fallback / imported
2. chay mot Apify batch that va luu run ID lam demo evidence
3. tach scheduler + scraper sang worker queue co Redis lease
4. them optional SSO/API auth cho pilot
5. backtest recommendation voi sales volume va elasticity khi co data
6. do manual minutes saved trong pilot thay vi dung proxy

Ba viec dau tien tang do tin cay nhieu hon viec them mot chatbot.
