# Hướng Dẫn Cấu Hình API, Langfuse & Quy Trình Đẩy Code Lên GitHub
*(Dành cho dự án GUARDIAN Pricing Command Center)*

Tài liệu này hướng dẫn cách thiết lập biến môi trường bảo mật, tích hợp các công cụ giám sát (Langfuse), cách chuẩn bị mã nguồn để đẩy lên GitHub an toàn và các bước chuẩn bị cho ngày thuyết trình (Build/Deploy).

---

## 1. Thiết Lập Biến Môi Trường (`.env`)

Mọi khóa API và cấu hình nhạy cảm tuyệt đối **KHÔNG** được lưu trực tiếp trong code. Hãy khai báo chúng ở file `.env` ở thư mục gốc của dự án.

### Các biến cấu hình chính trong `.env`:

```bash
# 1. OpenAI API Key (Sử dụng cho Pricing Agent và RAG tra cứu chính sách nhà cung cấp)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxx

# 2. Apify Scraper Token (Sử dụng để cào giá thực tế từ Shopee và Lazada)
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxxxxxxx

# 3. Cấu hình Langfuse (Giám sát, tracing toàn bộ suy luận và cuộc gọi LLM của Agent)
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

> [!IMPORTANT]
> Dự án đã có sẵn file [.env.example](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/.env.example). Khi tải dự án về máy mới, chỉ cần copy thành `.env` rồi điền key thật:
> ```powershell
> cp .env.example .env
> ```

---

## 2. Hướng Dẫn Tích Hợp Langfuse (Observability)

Langfuse giúp bạn theo dõi toàn bộ đường đi của Pricing Agent (Luồng suy luận, Tool calls, mức độ tiêu thụ Token LLM và độ trễ).

### Các bước lấy API Key trên Langfuse:
1. Truy cập **[Langfuse Cloud](https://cloud.langfuse.com/)** và đăng nhập/đăng ký tài khoản miễn phí.
2. Tạo một project mới với tên `Guardian Pricing Agent`.
3. Vào mục **Settings** ở thanh bên trái $\rightarrow$ Chọn **API Credentials** $\rightarrow$ Nhấp **Create API Keys**.
4. Sao chép 3 thông số: `Public Key`, `Secret Key` và `Host` rồi dán vào file `.env` của bạn.
5. Khởi động lại Backend FastAPI. Dự án sẽ tự động phát hiện các khóa này và bật tính năng trace. Bạn có thể mở dashboard Langfuse để xem các trace thời gian thực khi chạy Agent.

---

## 3. Quy Trình Đẩy Code Lên GitHub An Toàn

Để tránh rò rỉ mã bảo mật (API keys, file DB nội bộ chứa thông tin kinh doanh), hãy tuân thủ quy trình sau:

### Bước 3.1: Kiểm tra file `.gitignore`
Hãy chắc chắn rằng các file nhạy cảm sau đây đã nằm trong [.gitignore](file:///c:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/.gitignore):
* `.env` (Chứa API key thật)
* `backend/guardian.db` hoặc `*.db`, `*.sqlite` (File cơ sở dữ liệu SQLite chứa dữ liệu chạy thử)
* `node_modules/` (Thư viện frontend)
* `.venv/`, `.venv312/` (Môi trường ảo Python)
* `dist/`, `build/` (File đã được compile sau khi build frontend)

### Bước 3.2: Chuẩn bị đẩy code lên GitHub
Chạy các lệnh Git sau trong PowerShell tại thư mục gốc:

```powershell
# 1. Kiểm tra các tệp tin đang thay đổi
git status

# 2. Add tất cả thay đổi (chắc chắn không có tệp .env và file .db nào bị thêm vào)
git add .

# 3. Commit code kèm thông điệp rõ ràng
git commit -m "feat: configure rapid agent run options and update layout documentation"

# 4. Đẩy code lên nhánh chính
git push origin main
```

---

## 4. Danh Sách Kiểm Tra (Checklist) Cho Ngày Thuyết Trình Hackathon

Để đảm bảo buổi demo diễn ra trơn tru nhất trước ban giám khảo:

### 🛠️ Kế hoạch Dự phòng (Fallback Plan) cho Demo:
1. **Dữ liệu cào (Scraper API):** Các trang thương mại điện tử thường xuyên chặn IP nếu cào liên tục.
   * **Giải pháp:** Sử dụng tính năng chạy Agent nhanh mà tôi vừa tối ưu hóa (bằng cách bỏ tích chọn ô cào thực tế). Hệ thống sẽ tự động dùng dữ liệu đối thủ giả lập vô cùng thực tế và phản hồi chỉ trong 1-2 giây.
2. **LLM (OpenAI API):** Có thể gặp lỗi mạng hoặc hết hạn mức (quota) API.
   * **Giải pháp:** Hệ thống đã được viết sẵn giải pháp dự phòng (fallback rule-based). Nếu không có key OpenAI hoặc mạng bị lỗi, Agent vẫn chạy tốt dựa trên các ngưỡng cứng tự động tính toán từ cấu hình để sinh đề xuất.

### 🚀 Quy trình chuẩn bị chạy Demo trực tiếp:
* **Bước 1:** Kích hoạt Server Backend (`FastAPI`) và Frontend (`npm run dev`).
* **Bước 2:** Vào màn hình **Configuration** $\rightarrow$ Bấm nút màu đỏ **`Reset & Re-seed CSDL mẫu`** để đảm bảo dữ liệu sạch và sẵn sàng.
* **Bước 3:** Show màn hình **Mission Control / Overview** cho khán giả thấy tình trạng chênh lệch giá (CPI cao, nhiều Alert).
* **Bước 4:** Vào **AI Agent Workspace** $\rightarrow$ Bấm **`Chạy autonomous agent`** để Agent tự động tính toán margin và đưa ra đề xuất.
* **Bước 5:** Bấm **`Duyệt Khớp Giá`** hoặc **`Xem Thư Đề Xuất`** để demo luồng Human-in-the-loop hoàn chỉnh.
