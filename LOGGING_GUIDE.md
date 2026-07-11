# Logging Guide

Tài liệu này mô tả cách xem log cho các tiến trình trong dự án `Guardian Pricing Platform`.

## Mục tiêu

- Xem log realtime của Backend, Frontend và Docker services
- Xác định nhanh lỗi crash, lỗi port, lỗi import, lỗi scrape
- Biết file log nào cần mở khi dashboard hoặc API hoạt động bất thường

## Các file log hiện có

### Backend

- [backend_boot.out.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_boot.out.log)
- [backend_boot.err.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_boot.err.log)
- [backend_uvicorn.out](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_uvicorn.out)
- [backend_uvicorn.err](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_uvicorn.err)
- [backend_uvicorn_8002.out](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_uvicorn_8002.out)
- [backend_uvicorn_8002.err](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/backend_uvicorn_8002.err)

### Frontend

- [frontend_boot.out.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend_boot.out.log)
- [frontend_boot.err.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend_boot.err.log)
- [frontend_vite.out.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend_vite.out.log)
- [frontend_vite.err.log](/F:/JOB%20/GenAI%20Fund%20-%20HACKATHON/P3_TRACK-DETAIL-AND-HOSPILALITY/frontend_vite.err.log)

## Xem log realtime

Mở PowerShell tại thư mục gốc project và dùng:

```powershell
Get-Content .\backend_boot.out.log -Wait
```

```powershell
Get-Content .\backend_boot.err.log -Wait
```

```powershell
Get-Content .\frontend_boot.out.log -Wait
```

```powershell
Get-Content .\frontend_boot.err.log -Wait
```

`-Wait` tương tự lệnh `tail -f` trên Linux, rất hữu ích khi bạn vừa chạy server vừa muốn xem log đổ ra liên tục.

## Xem nhanh log gần nhất

Xem 50 dòng cuối:

```powershell
Get-Content .\backend_boot.out.log -Tail 50
Get-Content .\backend_boot.err.log -Tail 50
Get-Content .\frontend_boot.out.log -Tail 50
Get-Content .\frontend_boot.err.log -Tail 50
```

Xem 200 dòng cuối:

```powershell
Get-Content .\backend_boot.out.log -Tail 200
```

## Lọc log theo từ khóa

Tìm lỗi `Traceback`, `ERROR`, `Rejected scraper payload`, `fallback`:

```powershell
Select-String -Path .\backend_boot.out.log -Pattern "ERROR|Traceback|Rejected scraper payload|fallback"
```

```powershell
Select-String -Path .\backend_boot.err.log -Pattern "ERROR|Traceback|ModuleNotFoundError|Address already in use"
```

Tìm log liên quan scrape:

```powershell
Select-String -Path .\backend_boot.out.log -Pattern "Pre-upsert competitor payloads|scraper|Apify|fallback"
```

## Xem log Docker

Xem toàn bộ services:

```powershell
docker compose logs -f
```

Xem riêng Postgres:

```powershell
docker compose logs -f postgres
```

Xem riêng Redis:

```powershell
docker compose logs -f redis
```

Nếu bạn không chắc tên service trong `docker-compose.yml`, dùng:

```powershell
docker compose ps
```

## Xem tiến trình đang chiếm cổng

### Backend port 8001

```powershell
Get-NetTCPConnection -LocalPort 8001 | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

### Frontend port 3000

```powershell
Get-NetTCPConnection -LocalPort 3000 | Select-Object LocalAddress,LocalPort,State,OwningProcess
```

Xem tên tiến trình từ PID:

```powershell
Get-Process -Id <PID>
```

Ví dụ:

```powershell
Get-Process -Id 12345
```

## Chạy server để thấy log trực tiếp trên terminal

### Backend

```powershell
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Frontend

```powershell
cd frontend
npm run dev
```

Khi chạy kiểu này, log sẽ in trực tiếp ra terminal thay vì chỉ nằm trong file.

## Những dấu hiệu quan trọng cần chú ý

### Backend

- `Traceback`
- `ModuleNotFoundError`
- `Address already in use`
- `Rejected scraper payload due to product mismatch`
- `Pre-upsert competitor payloads`
- lỗi kết nối DB như `connection refused`

### Frontend

- `Failed to fetch`
- `Network Error`
- lỗi `Vite`
- lỗi build hoặc import module

### Docker

- Postgres chưa ready
- Redis crash loop
- container restart liên tục

## Khi dashboard không lên dữ liệu

Kiểm tra theo thứ tự:

1. Backend health:

```powershell
curl http://localhost:8001/api/v1/health
```

2. Log backend:

```powershell
Get-Content .\backend_boot.err.log -Tail 100
```

3. Log frontend:

```powershell
Get-Content .\frontend_boot.err.log -Tail 100
```

4. Dữ liệu scrape:

```powershell
Select-String -Path .\backend_boot.out.log -Pattern "Pre-upsert competitor payloads|fallback|Rejected scraper payload"
```

## Khi nghi ngờ lỗi scrape

Các từ khóa đáng kiểm tra trong log:

- `fallback`
- `Rejected scraper payload`
- `Pre-upsert competitor payloads`
- `Apify`
- `product mismatch`

Nếu các dòng này xuất hiện nhiều, thường có 1 trong các nguyên nhân:

- raw payload sai platform
- tên SKU không match đủ mạnh
- link discovery sinh sai URL
- fixture hoặc actor chưa phủ đủ dữ liệu

## Gợi ý workflow debug nhanh

1. Mở 1 cửa sổ theo dõi backend realtime

```powershell
Get-Content .\backend_boot.out.log -Wait
```

2. Mở 1 cửa sổ theo dõi frontend realtime

```powershell
Get-Content .\frontend_boot.out.log -Wait
```

3. Mở dashboard và bấm `Query market data`

4. Nếu không thấy dữ liệu, kiểm tra ngay:

```powershell
Get-Content .\backend_boot.err.log -Tail 100
```

5. Nếu nghi scrape sai SKU:

```powershell
Select-String -Path .\backend_boot.out.log -Pattern "Rejected scraper payload|Pre-upsert competitor payloads"
```

## Ghi chú

- File log có thể chứa dữ liệu cũ từ các lượt chạy trước
- Nếu muốn kiểm tra một vòng scrape sạch, nên dọn log cũ hoặc xem theo mốc thời gian mới nhất
- Trong môi trường demo hiện tại, dữ liệu có thể đến từ Apify live hoặc fixture fallback theo platform
