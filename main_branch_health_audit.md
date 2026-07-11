# Main Branch Health Audit

## 1. Audit Timestamp

- Thời điểm kiểm toán: `2026-07-11 15:50:35 +07:00`
- Phạm vi: nhánh `main` hiện tại trong workspace `P3_TRACK-DETAIL-AND-HOSPILALITY`
- Ghi chú quan trọng: `TESTING_GUIDE.md` không tồn tại trong workspace hiện tại, nên phần đối chiếu pre-merge được suy ra từ code hiện hành, test suite và tài liệu kỹ thuật còn lại.

## 2. Current Feature Matrix

| Hạng mục | Trạng thái trên `main` | Bằng chứng thực tế |
|---|---:|---|
| Backend FastAPI khởi động được | Pass | `GET /` trả `200` với payload `{"status":"healthy", ...}` |
| Docker stack cục bộ | Pass | `docker compose up -d` kéo image `postgres:15-alpine` và khởi động `guardian_postgres`, `guardian_redis`, `guardian_pgadmin` |
| Import CSV / dataset | Pass | `POST /api/v1/products/import-csv` và `POST /api/v1/products/import-dataset` được khai báo trong `backend/app/routes/products.py` |
| Seed demo dataset | Pass | `POST /api/v1/products/seed-demo` tồn tại và `backend/tests/test_demo_seed.py` đang pass |
| Dynamic ingestion alias mapping | Pass | `backend/app/services/data_ingestion.py` map được barcode/name/category/guardian_price/cost_price/image_url/description và competitor URL fields |
| Marketplace normalization | Pass | `backend/app/services/platform_mappers.py` chuẩn hóa `raw_price`, `net_price`, `discount`, `voucher_details`, `promo_mechanics`, `stock_status`, `rating` |
| Hybrid competitor scraping pipeline | Pass | `backend/app/scraper/scraper_engine.py` có luồng Apify, Crawl4AI, Playwright và fallback simulator |
| Link discovery | Pass | `backend/app/services/link_discovery.py` tự sinh search URL cho Shopee, Lazada, TikTok Shop, GrabMart, Pharmacity, Hasaki |
| Scraper status endpoint | Pass | `GET /api/v1/scraper/status` có trong `backend/app/routes/scraper.py` |
| Branch sample evidence endpoint | Pass | `GET /api/v1/scraper/branch-samples` có trong `backend/app/routes/scraper.py` |
| Sync price endpoint | Pass | `POST /api/v1/sync/sync-price/{barcode}` được khai báo trong `backend/app/routes/sync.py` |
| CPI calculation and alerting | Pass | `backend/app/services/cpi_calculator.py` đang tính CPI, recommendation và alert |
| Test suite backend | Pass | `9 passed` trong `backend/tests` khi chạy bằng `.venv` |
| `GET /api/v1/health` | Fail / Missing | Endpoint này không được khai báo trong `backend/app/main.py` hoặc các router đã quét; smoke request trả `404` |
| `backend/seed_db.py` | Fail / Missing | File không tồn tại ở root `backend` nên lệnh yêu cầu không thể chạy |
| `backend/app/routes/ingest.py` | Fail / Missing | File không tồn tại; ingestion thực tế nằm ở `backend/app/routes/products.py` + `backend/app/services/data_ingestion.py` |
| `backend/app/services/scrapers/base.py` | Fail / Missing | Không có file nguồn; thư mục `backend/app/services/scrapers/` chỉ còn `__pycache__` |
| `backend/app/services/scrapers/factory.py` | Fail / Missing | Không có file nguồn; không thấy registry/factory scraper kiểu cũ |
| `backend/app/services/scrapers/strategies/*.py` | Fail / Missing | Không có source `.py` cho hasaki/pharmacity/lazada/shopee/tiktok; chỉ còn cache artifacts |

### Feature notes

- Import hiện tại không còn là stub: `data_ingestion.py` parse CSV/JSON, xử lý alias field, dedupe barcode, auto-generate competitor links.
- Barcode được giữ dưới dạng chuỗi trong model và ingestion, nên logic code hiện tại không chủ động làm mất leading zero.
- Các trường sâu như `promo_mechanics` và `stock_status` đã được mô hình hóa ở lớp price observation (`CompetitorPrice`) và mapper, nhưng chưa đi qua luồng dataset ingestion.
- `TESTING_GUIDE.md` không có trong workspace, nên không thể đối chiếu literal từng mục của tài liệu đó; phần so sánh bên dưới dựa trên code và test hiện hữu.

## 3. Detected Anomalies & Logs

### 3.1 `docker compose up -d`

Kết quả:

- Docker stack đã lên thành công.
- Có cảnh báo cấu hình:

```text
time="2026-07-11T15:44:03+07:00" level=warning msg="F:\\JOB\\GenAI Fund - HACKATHON\\P3_TRACK-DETAIL-AND-HOSPILALITY\\docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion"
```

- Các container chính đã khởi động:

```text
Image postgres:15-alpine Pulled
Container guardian_redis Running
Container guardian_postgres Recreate
Container guardian_postgres Recreated
Container guardian_pgadmin Running
Container guardian_postgres Starting
Container guardian_postgres Started
```

### 3.2 `python backend/seed_db.py`

Kết quả:

```text
C:\Users\duy62\AppData\Local\Programs\Python\Python311\python.exe: can't open file 'F:\\JOB\\GenAI Fund - HACKATHON\\P3_TRACK-DETAIL-AND-HOSPILALITY\\backend\\seed_db.py': [Errno 2] No such file or directory
```

Diễn giải:

- Đây là lỗi missing artifact thật, không phải lỗi runtime của seed logic.
- Trên `main`, seeding demo hiện đã được chuyển sang `backend/app/services/demo_seed.py` và route `/api/v1/products/seed-demo`.

### 3.3 Backend startup trên `8001`

Khi chạy backend bằng `.venv` để smoke test, tiến trình có thể khởi động nhưng gặp xung đột port khi cổng `8001` đã có process khác giữ socket:

```text
INFO:     Started server process [9352]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8001): only one usage of each socket address (protocol/network address/port) is normally permitted
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
```

Một lần kiểm tra khác cho thấy backend thực tế đang phục vụ trên `8001` từ một process Python khác trong hệ thống:

```text
TCP    127.0.0.1:8001         0.0.0.0:0              LISTENING       14124
```

### 3.4 `GET /api/v1/health`

Kết quả smoke request:

```text
The remote server returned an error: (404) Not Found.
HTTP_STATUS=404
```

Diễn giải:

- Đây là thiếu hụt API thật trên `main`, không phải crash của server.
- Backend hiện chỉ có route root `/` trả payload healthy; chưa thấy router nào khai báo `/api/v1/health`.

### 3.5 Test suite

Chạy `pytest tests -q` trong `backend` bằng `.venv`:

```text
9 passed, 1 warning in 4.65s
```

Warning đáng chú ý:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

## 4. Merge Risk Analysis

### 4.1 Điểm gãy cấu trúc khi merge kỹ thuật từ `branch_of_Duy`

1. `backend/app/scraper/scraper_engine.py`
   - Hiện đang là trung tâm scraper hybrid một file.
   - Nếu `branch_of_Duy` mang thêm parser riêng cho từng platform, đây là điểm xung đột cao nhất vì logic hiện tại đã bao gồm Apify, Crawl4AI, Playwright và fallback simulator.

2. `backend/app/routes/scraper.py`
   - Router này giữ status runtime, background task, trigger endpoint và branch-sample evidence endpoint.
   - Nếu nhánh kia thay đổi cách trigger scrape hoặc status payload, conflict rất dễ xảy ra.

3. `backend/app/routes/products.py`
   - Route import CSV/dataset và seed demo đang đặt ở đây.
   - Bất kỳ merge nào thêm route `ingest.py` mới hoặc đổi shape response đều có khả năng gây ghi đè endpoint.

4. `backend/app/services/data_ingestion.py`
   - Đây là parser ingest thực tế.
   - Nguy cơ conflict lớn ở alias mapping, price parsing và competitor URL extraction.

5. `backend/app/services/platform_mappers.py`
   - Mapper này đang chuẩn hóa `promo_mechanics`, `stock_status`, `voucher_details`, `net_price`.
   - Nếu branch mới thêm field sâu hơn hoặc đổi naming convention, đây là nơi dễ đụng schema nhất.

6. `backend/app/services/link_discovery.py`
   - Search URL templates cho từng platform đang hardcode ở đây.
   - Nếu branch_of_Duy mang selector discovery/matching logic mới, file này có thể bị thay đổi trực tiếp.

7. `backend/app/services/demo_seed.py`
   - Seed demo hiện phụ thuộc `data/sku_master.csv` và `data/competitor_mock.csv`.
   - Nếu branch kia thay dataset topology hoặc schema seed, conflict dữ liệu rất dễ phát sinh.

8. `backend/app/services/scraped_samples.py`
   - Đây là adapter evidence cho branch-based sample data.
   - Nếu branch_of_Duy bổ sung dataset JSON mới, file này sẽ cần merge cẩn thận.

9. `backend/app/main.py`
   - Router registration hiện không có `/api/v1/health`.
   - Nếu branch mới thêm health endpoint hoặc đổi prefix, cần tránh trùng route/duplicate include_router.

10. `backend/app/config.py`
    - App hiện mặc định `USE_SQLITE=True`.
    - Nếu merge target chuyển sang Postgres làm mặc định, cần kiểm tra lại `engine`, seed flow và startup assumptions.

### 4.2 Các vùng thiếu hụt so với mô hình branch-based scraper truyền thống

- `backend/app/services/scrapers/base.py` và `factory.py` không còn source thật.
- `backend/app/services/scrapers/strategies/` không có file parser `.py` cho Hasaki, Pharmacity, Lazada, Shopee, TikTok Shop.
- Điều này cho thấy `main` hiện đã chuyển sang kiến trúc monolithic hybrid scraper thay vì strategy package rõ ràng.
- Khi merge nhánh khác vào, cần quyết định rõ:
  - giữ monolithic engine,
  - hay tách lại strategy layer có registry/factory.

### 4.3 Rủi ro dữ liệu và selector

- Selector HTML hiện đang hardcode trong `backend/app/scraper/scraper_engine.py` cho Hasaki/TikTok Shop, nên rất nhạy với DOM drift.
- Pharmacity/GrabMart đang lệ thuộc vào markdown extraction và regex, nên chất lượng sẽ dao động theo layout thay đổi.
- `platform_mappers.py` đã có xử lý `stock_status` và `promo_mechanics`, nhưng nếu branch_of_Duy thêm promotion detail sâu hơn, file này sẽ cần hợp nhất schema cẩn thận.
- Ingestion hiện không mang theo các field deep commerce như promotion/stock detail từ CSV upload; các field này chỉ xuất hiện ở lớp price observation.

### 4.4 Kết luận merge risk

- Mức độ rủi ro: `High` ở lớp scraper orchestration và mapper, `Medium` ở lớp ingestion/seed, `Low` ở lớp schema model vì tests hiện đang pass.
- Điểm cần chốt trước merge:
  - one-source-of-truth cho scraper registry,
  - thống nhất `health` endpoint,
  - thống nhất đường đi của ingest route,
  - xác nhận schema deep fields giữa upload data và scraped observations.

## 5. Bottom Line

- `main` hiện tại ở trạng thái **chạy được** và **test suite xanh**.
- Không có `backend/seed_db.py`, `backend/app/routes/ingest.py`, hay `TESTING_GUIDE.md` trong workspace hiện tại.
- Backend root endpoint hoạt động, nhưng `GET /api/v1/health` chưa tồn tại.
- Vùng merge nguy hiểm nhất là scraper stack và normalization stack, không phải model/schema core.
