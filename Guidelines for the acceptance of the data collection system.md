## TẦNG 1: KHỞI ĐỘNG CƠ SỞ DỮ LIỆU DOCKER (Terminal 1)
Mục tiêu: Kích hoạt Postgres container chạy ngầm ổn định trên cổng 5432.

1. Mở Terminal đầu tiên và di chuyển tới thư mục gốc (root) của dự án nơi có file docker-compose.yml.

2. Thực hiện lệnh khởi chạy các container (PostgreSQL, Redis):

```bash
docker compose up -d
```

3. Kiểm tra xem các container đã khởi động thành công và khoẻ mạnh chưa:

```bash
docker ps
```
(Nếu thấy trạng thái container báo Up và cổng 5432 đang mở là hoàn hảo).

## TẦNG 2: KHỞI ĐỘNG FASTAPI BACKEND (Terminal 2)
Mục tiêu: Nạp dữ liệu mồi và chạy server API trên cổng chiến lược 8001.

1. Mở Terminal thứ hai, di chuyển vào thư mục backend:

```Bash
cd backend
```
2. Kích hoạt môi trường ảo Python (Virtual Environment):

Trên Windows:

```Bash
.\venv\Scripts\activate
```
Trên macOS / Linux:

```Bash
source venv/bin/activate
```
3. Nạp dữ liệu mồi (Seed Data) vào Postgres: (Chỉ cần chạy lệnh này 1 lần duy nhất để tạo bảng và đổ dữ liệu La Roche-Posay, Vaseline... ban đầu):

```Bash
python seed_db.py
```
4. Khởi chạy server Backend trỏ đúng cổng 8001:

```Bash
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
(Giữ nguyên Terminal này để xem log thời gian thực khi test).

## TẦNG 3: KHỞI ĐỘNG FRONTEND REACT (Terminal 3)
Mục tiêu: Chạy giao diện Dashboard tương tác kết nối với Backend.

1. Mở Terminal thứ ba, di chuyển vào thư mục frontend:

```Bash
cd frontend
```
2. Cài đặt các gói thư viện cần thiết (nếu là lần đầu tiên chạy hoặc Codex vừa sửa dependencies):

```Bash
npm install
```
3. Khởi chạy môi trường phát triển của React (Vite):

```Bash
npm run dev
```

# 🚀 BẮT ĐẦU TEST HỆ THỐNG
Sau khi hoàn thành 3 tầng trên, bạn mở trình duyệt và thực hiện test theo đúng kịch bản bảo vệ:

1. Vào giao diện chính: Truy cập đường dẫn Frontend được hiển thị ở Terminal 3 (thường là http://localhost:5173 hoặc http://localhost:3000). Màn hình Dashboard Dark Mode sẽ hiện lên với biểu đồ lịch sử giá.

2. Kiểm tra API thông suốt: Truy cập http://127.0.0.1:8001/docs (Swagger UI). Bạn thử tìm endpoint POST /api/v1/sync/all hoặc POST /api/v1/ingest, bấm Try it out để chạy thử.

3. Thử nghiệm Force Sync: Trên giao diện dashboard React, chọn một sản phẩm và click vào nút "Force Sync" hoặc bấm nút "Kích hoạt chiến dịch quét giá toàn sàn". Lập tức chuyển sang nhìn màn hình Terminal 2 (Backend) để thấy log nạp payload cứu sinh (Fallback Fixture) nhảy liên tục cực kỳ sống động!
