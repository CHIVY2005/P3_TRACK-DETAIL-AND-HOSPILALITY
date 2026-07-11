# Hướng dẫn tự kiểm tra hệ thống Guardian Pricing Platform

Tài liệu này mô tả quy trình kiểm thử hệ thống hiện tại của `branch_of_Duy_v2`, từ khởi động hạ tầng đến kiểm tra backend, frontend, ingestion và luồng scraper/agent.

Mục tiêu của guide này:
- xác nhận hạ tầng Docker lên đúng
- xác nhận backend FastAPI chạy được
- xác nhận frontend Vite chạy được
- xác nhận ingestion và seed hoạt động
- xác nhận health check, sync và scraper endpoints trả phản hồi hợp lệ

---

## 1. Điều kiện tiên quyết

Trước khi test, hãy đảm bảo máy của bạn có:

- Docker Desktop đang chạy
- Python đã cài
- Node.js đã cài
- Dự án đã được clone đầy đủ
- File dữ liệu mẫu còn tồn tại tại `mock_data/guardian_master_sku.csv`

Nếu bạn đang dùng môi trường ảo Python, hãy ưu tiên chạy bằng `.venv` của dự án.

---

## 2. Kiểm tra cấu trúc quan trọng

Bạn nên xác nhận các file chính sau còn tồn tại:

- `backend/app/main.py`
- `backend/app/routes/ingest.py`
- `backend/app/routes/products.py`
- `backend/app/routes/scraper.py`
- `backend/app/routes/sync.py`
- `backend/app/services/apify_client.py`
- `backend/app/services/data_ingestion.py`
- `backend/app/services/link_discovery.py`
- `backend/app/services/scrapers/base.py`
- `backend/app/services/scrapers/factory.py`
- `backend/app/services/scrapers/strategies/`
- `backend/data/apify_fallback_fixture.json`
- `mock_data/guardian_master_sku.csv`

Nếu thiếu một trong các file này, cần khôi phục trước khi test.

---

## 3. Bước 1 - Khởi động database và Redis bằng Docker

Mở terminal tại thư mục gốc của project rồi chạy:

```powershell
docker compose up -d
```

### Kết quả mong đợi

- Container PostgreSQL chạy ở chế độ nền
- Container Redis chạy ở chế độ nền
- Không có lỗi nghiêm trọng

### Cách kiểm tra nhanh

```powershell
docker compose ps
```

Bạn nên thấy:
- `guardian_postgres`
- `guardian_redis`
- `guardian_pgadmin`

### Ghi chú

Trong trạng thái hiện tại, `docker-compose.yml` đang dùng `postgres:16-alpine` để khớp với data volume sẵn có.

---

## 4. Bước 2 - Khởi động backend FastAPI

Mở terminal mới ở thư mục `backend/` rồi chạy:

```powershell
& "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Kết quả mong đợi

- Backend khởi động tại `http://127.0.0.1:8001`
- Terminal hiển thị:
  - `Application startup complete`
  - `Uvicorn running on http://127.0.0.1:8001`

### Lưu ý

- Giữ terminal này mở trong suốt quá trình test backend.
- Nếu gặp lỗi `Address already in use`, hãy dừng tiến trình đang giữ cổng 8001 rồi chạy lại.

---

## 5. Bước 3 - Khởi động frontend Vite

Mở terminal mới ở thư mục `frontend/` rồi chạy:

```powershell
npm run dev -- --host 127.0.0.1 --port 3000
```

### Kết quả mong đợi

- Frontend chạy tại `http://127.0.0.1:3000`
- Terminal hiển thị Vite ready

### Cách kiểm tra nhanh

Mở trình duyệt và truy cập:

- `http://127.0.0.1:3000`

---

## 6. Bước 4 - Kiểm tra health check của backend

### 6.1 Root endpoint

```powershell
Invoke-RestMethod http://127.0.0.1:8001/
```

Kết quả mong đợi:

```json
{
  "status": "healthy",
  "project": "Guardian Pricing Intelligence Platform",
  "docs": "/docs",
  "version": "1.0.0"
}
```

### 6.2 Health endpoint

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
```

Kết quả mong đợi:
- `status: healthy`
- `api_base: /api/v1`
- `database_url`
- `fallback_fixture: true`

### Ý nghĩa

Nếu bước này pass, backend và cấu hình DB đã sẵn sàng.

---

## 7. Bước 5 - Mở tài liệu API tự sinh

Truy cập:

- `http://127.0.0.1:8001/docs`

### Kết quả mong đợi

- Swagger UI xuất hiện
- Bạn thấy danh sách endpoints như:
  - Products
  - Pricing
  - Alerts
  - Scraper Controls
  - AI Agent Workspace
  - Ingestion
  - Sync

---

## 8. Bước 6 - Test ingestion bằng file CSV thật

### 8.1 File đầu vào

Dùng file:

- `mock_data/guardian_master_sku.csv`

### 8.2 Endpoint

- `POST /api/v1/products/import-csv`

### 8.3 Cách test bằng PowerShell

```powershell
$env:PYTHONIOENCODING='utf-8'
@'
import requests
from pathlib import Path

url = 'http://127.0.0.1:8001/api/v1/products/import-csv'
file_path = Path('mock_data/guardian_master_sku.csv')

with file_path.open('rb') as f:
    files = {'file': (file_path.name, f, 'text/csv')}
    r = requests.post(url, files=files, timeout=120)

print(r.status_code)
print(r.text)
'@ | & "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -
```

### 8.4 Kết quả mong đợi

- HTTP status: `201`
- Response có dạng:

```json
{
  "status": "success",
  "format": "csv",
  "received": 200,
  "imported": 191,
  "skipped": 9,
  "competitor_links": 0
}
```

### 8.5 Ý nghĩa

- File CSV được đọc thành công
- Dữ liệu được map cột đúng
- Bản ghi được lưu vào database

---

## 9. Bước 7 - Test ingestion fuzzy mapping bằng route mới

Backend hiện có thêm route:

- `POST /api/v1/ingest/upload`

Route này dùng fuzzy mapping cho header CSV/JSON.

### Cách test nhanh

```powershell
$env:PYTHONIOENCODING='utf-8'
@'
import requests
from pathlib import Path

url = 'http://127.0.0.1:8001/api/v1/ingest/upload'
file_path = Path('mock_data/guardian_master_sku.csv')

with file_path.open('rb') as f:
    files = {'file': (file_path.name, f, 'text/csv')}
    r = requests.post(url, files=files, timeout=120)

print(r.status_code)
print(r.text)
'@ | & "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -
```

### Kết quả mong đợi

- HTTP status: `201`
- Response trả về `mapped_columns` và kết quả ingest

---

## 10. Bước 8 - Kiểm tra dữ liệu đã vào database hay chưa

Sau khi ingestion thành công, bạn nên kiểm tra DB trực tiếp.

### Mở Python shell trong backend

```powershell
@'
from app.db.session import SessionLocal
from app.db.models import Product

db = SessionLocal()
try:
    rows = db.query(Product).order_by(Product.barcode.asc()).all()
    print('COUNT=', len(rows))
    for row in rows[:5]:
        print(row.barcode, repr(row.name), row.category, row.guardian_price)
finally:
    db.close()
'@ | & "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -
```

### Kết quả mong đợi

- Có số lượng bản ghi tương ứng với file đã nạp
- Barcode là chuỗi
- Guardian price là số

---

## 11. Bước 9 - Test barcode có số 0 đầu

### 11.1 File test nhỏ

```csv
barcode,name,category,guardian_price
0012345678901,Test Barcode Leading Zero,Skincare,385000
```

### 11.2 Gửi file lên ingest endpoint

```powershell
$env:PYTHONIOENCODING='utf-8'
@'
import requests
from io import BytesIO

csv_data = "barcode,name,category,guardian_price\n0012345678901,Test Barcode Leading Zero,Skincare,385000\n"
files = {'file': ('edge_case.csv', BytesIO(csv_data.encode('utf-8')), 'text/csv')}

r = requests.post('http://127.0.0.1:8001/api/v1/ingest/upload', files=files, timeout=120)
print(r.status_code)
print(r.text)
'@ | & "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -
```

### 11.3 Kiểm tra lại trong DB

```powershell
@'
from app.db.session import SessionLocal
from app.db.models import Product

db = SessionLocal()
try:
    row = db.query(Product).filter(Product.barcode == '0012345678901').first()
    print('FOUND=', row is not None)
    if row:
        print('BARCODE=', row.barcode)
        print('PRICE=', row.guardian_price)
finally:
    db.close()
'@ | & "F:\JOB\GenAI Fund - HACKATHON\P3_TRACK-DETAIL-AND-HOSPILALITY\.venv\Scripts\python.exe" -
```

### Kết quả mong đợi

- `FOUND = True`
- Barcode không bị mất số 0 đầu

---

## 12. Bước 10 - Test sync price

Endpoint:

- `POST /api/sync/sync-price/{barcode}`

Ví dụ:

- `POST /api/sync/sync-price/8933321819605?platform=Hasaki`

### Cách test

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/api/sync/sync-price/8933321819605?platform=Hasaki"
```

### Kết quả mong đợi

- HTTP status: `200`
- Response có `status: success`
- Có `updated_price`

---

## 13. Bước 11 - Test scraper trigger

Endpoint:

- `POST /api/v1/scraper/trigger`

### Cách test

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/scraper/trigger -ContentType "application/json" -Body '{}'
```

### Kết quả mong đợi

- `202 Accepted`
- Trả về trạng thái đã trigger pipeline

---

## 14. Bước 12 - Test trang frontend

Sau khi frontend chạy, mở:

- `http://127.0.0.1:3000`

### Bạn nên kiểm tra

- Sidebar có hiện không
- Tab Mission Control có render không
- Tab SKU Insights có render table/chart không
- Tab Agent Workspace có render không
- Tab Operations Config có render không

---

## 15. Bước 13 - Đối chiếu log và docs

Trong quá trình test, nên đối chiếu:

- `http://127.0.0.1:8001/docs`
- phản hồi API thực tế
- log terminal backend
- log terminal frontend

### Những thứ cần nhìn

- status code
- payload trả về
- dữ liệu đã ghi vào DB
- warning hoặc error trong log

---

## 16. Bước 14 - Cách dừng hệ thống sau khi test

### Dừng backend/frontend

```powershell
$ports = 8001,3000
$pids = foreach($port in $ports){
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -gt 0 } |
    Select-Object -ExpandProperty OwningProcess
}
$pids | Sort-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
```

### Dừng Docker containers

```powershell
docker compose down
```

---

## 17. Checklist nghiệm thu nhanh

- [ ] Docker Postgres/Redis đã chạy
- [ ] Backend khởi động thành công
- [ ] Frontend khởi động thành công
- [ ] `GET /` trả healthy
- [ ] `GET /api/v1/health` trả healthy
- [ ] `/docs` mở được
- [ ] Upload `mock_data/guardian_master_sku.csv` thành công
- [ ] Ingest route `/api/v1/ingest/upload` hoạt động
- [ ] DB có dữ liệu trong `Product`
- [ ] Barcode giữ nguyên số 0 đầu
- [ ] `sync-price` trả `success`
- [ ] Scraper trigger trả `202`
- [ ] Multi-tab frontend render bình thường

---

## 18. Kết luận

Nếu bạn chạy hết các bước trên và các kết quả mong đợi đều đạt, thì hệ thống đang ở trạng thái:

- backend hoạt động
- frontend hoạt động
- ingestion hoạt động
- database ghi nhận đúng dữ liệu
- scraper/sync pipeline hoạt động

Tức là hệ thống đã sẵn sàng để demo hoặc nghiệm thu.
