# Hướng dẫn tự kiểm tra hệ thống Guardian Pricing Platform

Tài liệu này hướng dẫn từng bước để bạn tự tay test hệ thống từ lúc khởi động cho đến lúc kiểm tra dữ liệu trong database.

Mục tiêu của guide này:
- xác nhận backend chạy được
- xác nhận frontend chạy được
- xác nhận API ingestion hoạt động
- xác nhận dữ liệu được ghi vào PostgreSQL đúng kiểu
- xác nhận luồng scraper/agent/link discovery hoạt động với fallback fixture

---

## 1. Điều kiện tiên quyết

Trước khi test, hãy đảm bảo máy của bạn có:

- Docker Desktop đang chạy
- Python đã cài
- Node.js đã cài
- Dự án đã được clone đầy đủ
- File dữ liệu mẫu còn tồn tại tại:
  - `mock_data/guardian_master_sku.csv`

Nếu bạn đang dùng môi trường ảo Python, hãy ưu tiên chạy bằng `.venv` của dự án.

---

## 2. Kiểm tra cấu trúc thư mục quan trọng

Bạn nên xác nhận các file chính sau còn tồn tại:

- `backend/app/main.py`
- `backend/app/routes/ingest.py`
- `backend/app/routes/agent.py`
- `backend/app/services/apify_client.py`
- `backend/app/services/link_discovery.py`
- `backend/data/apify_fallback_fixture.json`
- `mock_data/guardian_master_sku.csv`

Nếu thiếu một trong các file này, bạn cần khôi phục trước khi test.

---

## 3. Bước 1 — Khởi động database và Redis bằng Docker

Mở terminal tại thư mục gốc của project rồi chạy:

```powershell
# file: terminal
docker compose up -d db redis
```

### Kết quả mong đợi
- Container PostgreSQL chạy ở chế độ nền
- Container Redis chạy ở chế độ nền
- Không có lỗi nghiêm trọng

### Cách kiểm tra nhanh
Bạn có thể xem container đang chạy bằng:

```powershell
# file: terminal
docker ps
```

Nếu thấy các container kiểu `guardian_postgres` và `guardian_redis` thì bước này đã ổn.

---

## 4. Bước 2 — Khởi động backend FastAPI

Mở terminal mới ở thư mục gốc của project rồi chạy:

```powershell
# file: terminal
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

> Nếu bạn không dùng `.venv`, hãy thay bằng lệnh Python tương ứng trên máy của bạn.

### Kết quả mong đợi
- Backend khởi động tại `http://127.0.0.1:8001`
- Không có lỗi import
- Trình khởi động in ra trạng thái:
  - `Application startup complete`

### Lưu ý
- Giữ terminal này mở trong suốt quá trình test backend.
- Nếu bạn chạy ở background, hãy nhớ dừng bằng lệnh PowerShell phù hợp khi test xong.

---

## 5. Bước 3 — Khởi động frontend Vite

Mở terminal mới ở thư mục gốc của project rồi chạy:

```powershell
# file: terminal
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

### Kết quả mong đợi
- Frontend chạy tại `http://127.0.0.1:3000`
- Terminal hiển thị Vite ready

### Cách kiểm tra nhanh
Mở trình duyệt và truy cập:

- `http://127.0.0.1:3000`

Nếu trang UI hiện ra thì frontend đã chạy được.

---

## 6. Bước 4 — Test health check của backend

Đây là bước kiểm tra tối thiểu để biết backend và database config đã sẵn sàng.

### 6.1 Test root endpoint
Mở trình duyệt hoặc dùng PowerShell:

```powershell
# file: terminal
Invoke-RestMethod http://127.0.0.1:8001/
```

### Kết quả mong đợi
Bạn nhận được JSON tương tự:

```json
{
  "status": "healthy",
  "project": "Guardian Pricing Intelligence Platform",
  "docs": "/docs",
  "version": "1.0.0"
}
```

### 6.2 Test health endpoint
Chạy:

```powershell
# file: terminal
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
```

### Kết quả mong đợi
Bạn sẽ thấy JSON chứa:
- `status: healthy`
- `api_base: /api/v1`
- `database_url`
- `fallback_fixture: true`

### Ý nghĩa
Nếu bước này pass, backend đã kết nối và cấu hình xong.

---

## 7. Bước 5 — Mở tài liệu API tự sinh

Truy cập:

- `http://127.0.0.1:8001/docs`

### Kết quả mong đợi
- Swagger UI xuất hiện
- Bạn thấy danh sách endpoints như:
  - Products
  - Pricing
  - Alerts
  - Scraper
  - Agent
  - Ingestion
  - Sync

### Vì sao cần bước này
`/docs` giúp bạn test tay từng API mà không cần viết code.

---

## 8. Bước 6 — Test ingestion bằng file CSV thật

Đây là bước quan trọng nhất vì nó kiểm tra luồng ingest dữ liệu thật vào DB.

### 8.1 File đầu vào
Dùng file:

- `mock_data/guardian_master_sku.csv`

### 8.2 Endpoint
- `POST /api/v1/ingest/upload`

### 8.3 Cách test bằng PowerShell
Chạy lệnh sau ở thư mục gốc project:

```powershell
# file: terminal
$env:PYTHONIOENCODING='utf-8'
@'
import requests
from pathlib import Path

url = 'http://127.0.0.1:8001/api/v1/ingest/upload'
file_path = Path('mock_data/guardian_master_sku.csv')

with file_path.open('rb') as f:
    files = {'file': (file_path.name, f, 'text/csv')}
    r = requests.post(url, files=files, timeout=60)

print(r.status_code)
print(r.text)
'@ | .\.venv\Scripts\python.exe -
```

### 8.4 Kết quả mong đợi
- HTTP status: `200`
- Response có dạng:

```json
{
  "status": "success",
  "file_saved": "...guardian_master_sku.csv",
  "processed_records": 5,
  "upsert_target": "sku_master"
}
```

### 8.5 Ý nghĩa
- File CSV được đọc thành công
- Dữ liệu được map cột đúng
- Bản ghi được upsert vào `sku_master`

---

## 9. Bước 7 — Kiểm tra dữ liệu đã vào PostgreSQL hay chưa

Sau khi ingestion thành công, bạn nên kiểm tra DB trực tiếp.

### 9.1 Mở Python shell trong backend
Chạy:

```powershell
# file: terminal
Set-Location backend
@'
from app.db.session import SessionLocal
from app.db.models import SkuMaster

db = SessionLocal()
try:
    rows = db.query(SkuMaster).order_by(SkuMaster.barcode.asc()).all()
    print('COUNT=', len(rows))
    for row in rows:
        print(row.barcode, repr(row.product_name), row.category, row.guardian_price)
finally:
    db.close()
'@ | ..\.venv\Scripts\python.exe -
```

### 9.2 Kết quả mong đợi
- Có số lượng bản ghi tương ứng với file đã nạp
- Barcode là chuỗi
- Guardian price là số nguyên

### 9.3 Bạn cần nhìn gì
Kiểm tra các điểm sau:
- barcode có giữ nguyên số 0 đầu không
- product_name có đọc đúng tiếng Việt không
- guardian_price có bị thành float không

---

## 10. Bước 8 — Test barcode có số 0 đầu

Mục tiêu của bước này là xác minh hệ thống không làm mất leading zero.

### 10.1 File test nhỏ
Bạn có thể tạo một CSV tạm như sau:

```csv
barcode,product_name,category,guardian_price
0012345678901,Test Barcode Leading Zero,Skincare,385000.0
```

### 10.2 Gửi file lên ingest endpoint
Dùng script PowerShell:

```powershell
# file: terminal
$env:PYTHONIOENCODING='utf-8'
@'
import requests
from io import BytesIO

csv_data = "barcode,product_name,category,guardian_price\n0012345678901,Test Barcode Leading Zero,Skincare,385000.0\n"
files = {'file': ('edge_case.csv', BytesIO(csv_data.encode('utf-8')), 'text/csv')}

r = requests.post('http://127.0.0.1:8001/api/v1/ingest/upload', files=files, timeout=60)
print(r.status_code)
print(r.text)
'@ | .\.venv\Scripts\python.exe -
```

### 10.3 Kiểm tra lại trong DB
Chạy:

```powershell
# file: terminal
Set-Location backend
@'
from app.db.session import SessionLocal
from app.db.models import SkuMaster

db = SessionLocal()
try:
    row = db.query(SkuMaster).filter(SkuMaster.barcode == '0012345678901').first()
    print('FOUND=', row is not None)
    if row:
        print('BARCODE=', row.barcode)
        print('PRICE=', row.guardian_price)
finally:
    db.close()
'@ | ..\.venv\Scripts\python.exe -
```

### Kết quả mong đợi
- `FOUND = True`
- `BARCODE = 0012345678901`
- `PRICE = 385000`

### Ý nghĩa
- Barcode được xử lý dưới dạng string
- Hệ thống không mất số 0 đầu
- Price đã được chuẩn hóa về số nguyên

---

## 11. Bước 9 — Test AI Link Discovery

Bước này kiểm tra luồng background tạo link competitor và write-back vào DB.

### 11.1 Endpoint
- `POST /api/v1/agent/link-discovery/{barcode}`

Ví dụ:
- `POST /api/v1/agent/link-discovery/7612345678901`

### 11.2 Cách test
Chạy:

```powershell
# file: terminal
$env:PYTHONIOENCODING='utf-8'
@'
import requests
barcode = '7612345678901'
r = requests.post(f'http://127.0.0.1:8001/api/v1/agent/link-discovery/{barcode}', timeout=60)
print(r.status_code)
print(r.text)
'@ | .\.venv\Scripts\python.exe -
```

### 11.3 Kết quả mong đợi
- HTTP status: `202`
- Response kiểu:

```json
{
  "status": "accepted",
  "barcode": "7612345678901",
  "message": "Link discovery queued and fallback scraper triggered."
}
```

### 11.4 Kiểm tra DB
Chạy:

```powershell
# file: terminal
Set-Location backend
@'
from app.db.session import SessionLocal
from app.db.models import CompetitorLink

db = SessionLocal()
try:
    rows = db.query(CompetitorLink).filter(CompetitorLink.barcode == '7612345678901').all()
    print('LINK_COUNT=', len(rows))
    for row in rows:
        print(row.barcode, row.platform, row.url)
finally:
    db.close()
'@ | ..\.venv\Scripts\python.exe -
```

### Kết quả mong đợi
- Ít nhất 1 link được tạo
- URL fallback dạng Shopee search query

---

## 12. Bước 10 — Test scraper trigger

Nếu bạn muốn test luồng scraper background, dùng endpoint sau:

- `POST /api/v1/scraper/trigger`

### Cách test nhanh
Trong Swagger hoặc PowerShell:

```powershell
# file: terminal
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/scraper/trigger -ContentType "application/json" -Body '{}'
```

### Kết quả mong đợi
- `202 Accepted`
- Trả về trạng thái đã trigger pipeline

### Lưu ý
Nếu APIFY token không có, hệ thống sẽ dùng fallback fixture.

---

## 13. Bước 11 — Test agent run

Bạn có thể kích hoạt AI agent workspace bằng endpoint:

- `POST /api/v1/agent/run`

### Cách test
```powershell
# file: terminal
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/agent/run -ContentType "application/json" -Body '{}'
```

### Kết quả mong đợi
- `202 Accepted`
- Trả về một `AgentTask`
- Có log trạng thái queued hoặc running

### Khi nào nên test
- Sau khi DB có dữ liệu sản phẩm
- Khi muốn kiểm tra luồng background task của agent

---

## 14. Bước 12 — Test trang frontend

Sau khi frontend chạy, mở:

- `http://127.0.0.1:3000`

### Bạn nên kiểm tra
- Trang có load không
- Menu sidebar có hiện không
- Dữ liệu dashboard có gọi API backend được không
- Không có lỗi CORS

### Nếu gặp lỗi
Mở Developer Tools của trình duyệt và kiểm tra:
- Console
- Network

---

## 15. Bước 13 — Kiểm tra API docs và phản hồi thực tế

Trong quá trình test, nên đối chiếu:

- `http://127.0.0.1:8001/docs`
- API response thực tế
- Database output thực tế

### Những thứ cần đối chiếu
- status code
- payload trả về
- dữ liệu đã ghi vào DB
- log terminal backend

---

## 16. Bước 14 — Cách dừng hệ thống sau khi test

Nếu bạn đã chạy backend/frontend ở background hoặc muốn dừng toàn bộ service, dùng lệnh PowerShell sau:

```powershell
# file: terminal
$ports = 8001,3000
$pids = foreach($port in $ports){
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -gt 0 } |
    Select-Object -ExpandProperty OwningProcess
}
$pids | Sort-Object -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
```

Nếu muốn dừng Docker containers:

```powershell
# file: terminal
docker compose down
```

---

## 17. Checklist nghiệm thu nhanh

Bạn có thể tick checklist này khi tự test:

- [ ] Docker db/redis đã chạy
- [ ] Backend khởi động thành công
- [ ] Frontend khởi động thành công
- [ ] `GET /` trả healthy
- [ ] `GET /api/v1/health` trả healthy
- [ ] `/docs` mở được
- [ ] Upload `mock_data/guardian_master_sku.csv` thành công
- [ ] DB có dữ liệu trong `sku_master`
- [ ] Barcode giữ nguyên số 0 đầu
- [ ] Price lưu kiểu int
- [ ] Link discovery tạo được record trong `competitor_links`
- [ ] Scraper/agent endpoint trả đúng status

---

## 18. Kết luận

Nếu bạn chạy hết các bước trên và các kết quả mong đợi đều đạt, thì hệ thống của bạn đang ở trạng thái:

- backend hoạt động
- frontend hoạt động
- ingestion hoạt động
- database ghi nhận đúng dữ liệu
- fallback AI/scraper pipeline hoạt động

Tức là hệ thống đã sẵn sàng để demo hoặc nghiệm thu.
