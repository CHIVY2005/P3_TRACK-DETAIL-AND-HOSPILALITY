# Pitch Deck Draft

Tai lieu nay la khung pitch deck da duoc canh chinh theo trang thai code hien tai, khong theo boilerplate cu.

## Slide 1. Bai toan

Tieu de:

`Gia doi thu thay doi nhanh, nhung quyet dinh gia noi bo van qua thu cong`

Noi dung:

- Commercial team phai tu theo doi Shopee, Lazada, TikTok Shop, Hasaki, GrabMart
- Gia that cua doi thu khong chi la gia niem yet, ma con voucher, combo, flash sale
- Neu Guardian phan ung cham thi mat thi phan
- Neu Guardian giam gia cam tinh thi rot bien loi nhuan

Thong diep:

Can mot he thong vua nhin thay thi truong theo thoi gian gan that, vua kiem soat duoc margin.

## Slide 2. Giai phap

Tieu de:

`GUARDIAN Pricing Command Center`

Noi dung:

- mot single source of truth cho gia doi thu
- mot CPI engine de biet SKU nao dang overpriced / underpriced
- mot AI agent de de xuat hanh dong
- human-in-the-loop de giu quyen phe duyet

Thong diep:

Khong chi la dashboard. Day la mot vong dieu hanh quyet dinh gia.

## Slide 3. Kien truc MVP

So do nen ve:

```text
Dataset upload
  -> Product catalog
  -> CompetitorLink
  -> Hybrid scrape
  -> CompetitorPrice
  -> CPI + Alert engine
  -> Agent
  -> Approval UI
```

Diem can noi:

- ho tro nap `csv` va `json`
- neu thieu link doi thu thi co search-driven discovery
- scrape co fallback de he thong khong bi dung khi bi chan mang

## Slide 4. Cong nghe agentic AI

Tieu de:

`AI khong tu sua gia. AI de xuat, con nguoi phe duyet.`

Noi dung:

- `Market Observer` doc signal thi truong
- `Margin Guardian` tinh margin neu match gia
- `Supplier Negotiator` tao thu de nghi support gia
- `Orchestrator` dieu phoi toan bo phien chay

Thong diep:

Agent duoc tach thanh vai tro ro rang, giai thich duoc, trace duoc, va khong vuot qua quyen cua con nguoi.

## Slide 5. Luong quyet dinh

Noi dung:

1. ingest du lieu noi bo
2. discover link neu thieu
3. scrape hybrid
4. tinh CPI va tao alert
5. agent quyet dinh `match` hay `negotiate`
6. nguoi dung approve / reject

Diem hay can nhan manh:

- he thong tra loi truc tiep 4 cau hoi nghiep vu cua de bai
- khong can doi du lieu perfect moi chay duoc

## Slide 6. Demo story

Flow demo nen di:

1. vao `Operations Config`
2. bam seed demo hoac import dataset
3. sang `Mission Control`
4. show KPI, priority queue, reasoning trace
5. sang `SKU Insights` de show raw pricing va history
6. sang `Agent Workspace` de run agent
7. approve 1 `AUTO_PRICE_MATCH`
8. quay lai dashboard cho thay state thay doi

## Slide 7. Gia tri business

Noi dung:

- giam cong theo doi gia thu cong
- tang toc do phan ung voi doi thu
- tranh giam gia mu quang
- tao nen tang mo rong thanh pricing operating system

Thong diep:

Gia tri khong nam o viec "co AI". Gia tri nam o viec AI giup rut ngan thoi gian ra quyet dinh nhung van giu an toan business.

## Slide 8. Diem manh ky thuat

Noi dung:

- ingestion linh hoat
- competitor link registry
- hybrid scraping
- anomaly filter
- CPI + alert engine
- agent architecture tach folder
- approval workflow
- UI command center

## Slide 9. Gioi han va trung thuc ky thuat

Noi dung:

- link discovery hien tai moi la MVP
- scrape that chua o muc production 200 SKU
- queue worker, auth, audit log chua co

Thong diep:

He thong da giai quyet dung huong bai toan va da co duong nang cap ro rang.

## Slide 10. Huong di sau hackathon

Noi dung:

1. dua Postgres + pgvector thanh data mode chinh
2. nang cap link discovery thanh matching service
3. tach scraper va agent sang worker queue
4. them auth, audit log, va deployment
5. them co che goi ERP / CRM
