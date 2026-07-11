# Merge & Refactor Report

## Audit Timestamp

- `2026-07-11 16:48:18 +07:00`
- Working branch: `branch_of_Duy_v2`

## Backend Files Merged

### Overwritten or Added

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/db/models.py`
- `backend/app/schemas.py`
- `backend/app/scraper/scraper_engine.py`
- `backend/app/services/apify_client.py`
- `backend/app/services/demo_seed.py`
- `backend/app/services/scrapers/__init__.py`
- `backend/app/services/scrapers/base.py`
- `backend/app/services/scrapers/factory.py`
- `backend/app/services/scrapers/strategies/__init__.py`
- `backend/app/services/scrapers/strategies/grabmart.py`
- `backend/app/services/scrapers/strategies/hasaki.py`
- `backend/app/services/scrapers/strategies/lazada.py`
- `backend/app/services/scrapers/strategies/pharmacity.py`
- `backend/app/services/scrapers/strategies/shopee.py`
- `backend/app/services/scrapers/strategies/tiktok.py`
- `backend/app/core/mapping_config.json`
- `backend/app/routes/ingest.py`
- `backend/seed_db.py`

### Removed

- No source files were deleted from the working tree during this merge.

## Frontend Sync Status

- `frontend/src/api.js` was aligned to prefer `VITE_API_BASE_URL`, with fallback to `VITE_API_ORIGIN`.
- `react-toastify` was installed and recorded in `frontend/package.json` and `frontend/package-lock.json`.
- No UI binding breakage was found in the current `main` frontend tables/charts. The current UI already consumes:
  - `raw_price`
  - `discount`
  - `voucher_details`
  - `promo_mechanics`
  - `net_price`
  - `stock_status`
  - `is_suspicious`
  - `url`
- Production build succeeded with `vite build`.
- Vite dev server booted successfully on `http://127.0.0.1:5173`.

## Smoke Test Evidence

### Database bootstrap

- `docker compose up -d` completed successfully.
- `python backend/seed_db.py` now succeeds after schema compatibility fixes.

### API smoke

- `GET /api/v1/health`
  - Status: `200`
  - Payload:
    - `status: healthy`
    - `api_base: /api/v1`
    - `fallback_fixture: true`
- `POST /api/v1/products/import-csv`
  - Status: `201`
  - Result: imported `191` products from `data/sku_master.csv`
- `POST /api/sync-price/8933321819605?platform=Hasaki`
  - Status: `200`
  - Result: price sync completed successfully with `updated_price: 428507.0`

### UI smoke

- Vite dev server reported ready in `311 ms`.
- `vite build` completed successfully.

## Notable Fixes Applied

- Added OOP scraper contracts and strategy registry from `branch_of_Duy`.
- Reworked `backend/app/scraper/scraper_engine.py` into an adapter that:
  - uses Apify fallback logic safely,
  - normalizes data through strategy parsers,
  - persists `raw_payload` without breaking PostgreSQL/SQLite schema.
- Added schema compatibility handling for older SQLite files:
  - `stock_status`
  - `is_suspicious`
  - `voucher_details`
  - `promo_mechanics`
  - `url`
  - `raw_payload`
- Added `backend/app/routes/ingest.py` as a Pandas-based fuzzy mapping bridge.
- Added a safe `backend/seed_db.py` wrapper so the requested seed command now runs.

## E2E Readiness

- Functional readiness for dashboard demo: **Yes**
- Backend unit tests: **9 passed**
- Frontend build: **Passed**
- Backend smoke: **Passed**
- Remaining environment caveat:
  - Port `8001` is still occupied by an external/stale listener in the workspace, so the live smoke run was validated on `8002` instead.

## Final Assessment

The asymmetric integration is complete at the code level and the system is ready for dashboard presentation, with one environment-level caveat around the pre-existing `8001` listener.
