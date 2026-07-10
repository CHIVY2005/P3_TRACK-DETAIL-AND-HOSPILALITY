# CONFIG AND DEPLOY GUIDE

Tai lieu nay giai thich cach cau hinh moi truong, cach chay local, va nhung diem can biet khi demo hoac day code.

## 1. Bien moi truong

Tao file `.env` o thu muc goc.

Vi du:

```text
OPENAI_API_KEY=your_openai_key
APIFY_API_TOKEN=your_apify_token
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
USE_SQLITE=true
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=guardian_db
```

Luu y:

- `OPENAI_API_KEY` hien khong con la dependency bat buoc cho agent pricing rule-based
- neu khong co `APIFY_API_TOKEN`, scraper van chay theo fallback / simulated pricing
- neu khong co Langfuse keys, tracing tu dong tat

## 2. Database mode

Codebase hien tai uu tien `SQLite` de demo nhanh.

Neu:

```text
USE_SQLITE=true
```

thi app dung file:

```text
backend/guardian.db
```

Neu doi qua Postgres:

```text
USE_SQLITE=false
```

thi app se dung URI tao tu `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

## 3. Chay backend

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\activate
pip install -r backend\requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Swagger docs:

```text
http://127.0.0.1:8001/docs
```

## 4. Chay frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend mac dinh goi:

```text
http://localhost:8001/api/v1
```

Neu can doi:

```text
VITE_API_ORIGIN=http://localhost:8001
```

## 5. Chay demo nhanh

Thu tu de an toan:

1. chay backend
2. chay frontend
3. vao `Operations Config`
4. bam `Reload demo dataset`
5. sang `Mission Control`
6. trigger scrape hoac run agent

## 6. Import dataset that

Ho tro:

- `csv`
- `json`

Endpoint:

```text
POST /api/v1/products/import-dataset
```

Importer se:

- map field aliases
- tao `Product`
- tao `CompetitorLink` neu co URL doi thu
- scrape MVP cho tung SKU sau import

Field thuong dung:

```text
barcode
name
category
guardian_price
cost_price
image_url
description
shopee_url
lazada_url
hasaki_url
tiktok_url
grab_url
pharmacity_url
```

## 7. Seed demo

Route:

```text
POST /api/v1/products/seed-demo
```

Route nay:

- xoa du lieu cu
- doc `data/sku_master.csv`
- doc `data/competitor_mock.csv`
- insert lai data
- tinh CPI va alerts

## 8. Langfuse

Neu key hop le, he thong trace:

- root agent run
- per-alert span
- tool calls
- decision summary cho tung alert

Neu khong co key, nothing breaks. Chi la tracing tat.

## 9. Git hygiene

Can dam bao cac file sau khong bi commit:

- `.env`
- `*.db`
- `node_modules/`
- `.venv*`
- `dist/`
- `build/`

Quy trinh co ban:

```powershell
git status
git add .
git commit -m "docs: rewrite architecture documentation"
git push origin main
```

## 10. Demo fallback plan

Neu scrape that bi chan:

- dung fallback data trong scraper
- van co the demo full luong CPI -> alert -> agent -> approval

Neu frontend build bi vuong sandbox:

- uu tien chay `npm run dev`
- ghi chu ro day la issue moi truong Vite/esbuild, khong phai bug nghiep vu trong app

## 11. Gioi han moi truong hien tai

Trong workspace nay da tung gap:

- PowerShell block `npm.ps1`
  - workaround: dung `npm.cmd`
- Vite/esbuild co the loi khi doc parent directories trong sandbox

Hai diem nay nen duoc ghi nho de tranh mat thoi gian debug nham vao code app.
