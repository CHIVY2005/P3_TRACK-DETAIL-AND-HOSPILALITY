# HƯỚNG DẪN CẤU TRÚC BOILERPLATE & BÁO CÁO TÌNH TRẠNG MÃ NGUỒN (TECHNICAL EXPLANATION)

Tài liệu này giải thích chi tiết cấu trúc nền tảng của dự án (**Boilerplate**), tình trạng mã nguồn hiện tại, cùng các giải pháp nâng cao đã được tích hợp hoàn chỉnh để phục vụ cho buổi thuyết trình Hackathon.

---

## 📂 1. Cấu Trúc Khung Dự Án (Boilerplate Structure)

Bộ mã nguồn được tổ chức theo cấu trúc phân tách rõ ràng giữa **Frontend (React)** và **Backend (FastAPI)**:

```
P3_TRACK-DETAIL-AND-HOSPILALITY/
├── backend/                     # Mã nguồn máy chủ FastAPI & AI Agent
│   ├── app/
│   │   ├── config.py            # Quản lý tham số môi trường & cấu hình hệ thống
│   │   ├── db/
│   │   │   ├── database.py      # Cấu hình kết nối SQLAlchemy (SQLite/PostgreSQL)
│   │   │   └── models.py        # Các thực thể CSDL (Product, CompetitorPrice, Alert, Action, v.v.)
│   │   ├── routes/              # Các cổng API REST
│   │   │   ├── products.py      # Quản lý danh mục sản phẩm, nhập CSV và tính CPI
│   │   │   ├── scraper.py       # Kích hoạt quét giá và Reset hệ thống
│   │   │   └── agent.py         # Quản lý hàng đợi phê duyệt hành động (HITL) & Cấu hình AI
│   │   ├── schemas.py           # Định nghĩa kiểu dữ liệu truyền nhận (Pydantic models)
│   │   ├── scraper/
│   │   │   └── scraper_engine.py# Động cơ cào dữ liệu (Apify, Crawl4AI, Playwright & Simulator)
│   │   └── services/
│   │       ├── agent_engine.py  # Định nghĩa đồ thị trạng thái LangGraph của AI Agent
│   │       └── cpi_calculator.py# Thuật toán tính chỉ số CPI & Cảnh báo lệch giá
│   ├── data/                    # Nơi chứa các nguồn tài liệu tri thức & tệp cấu hình
│   │   ├── knowledge/
│   │   │   └── supplier_policies.txt # Tài liệu chính sách đền bù giá nhập (phục vụ RAG)
│   │   └── config.json          # Tệp lưu trữ tham số cấu hình động của Agent
│   ├── guardian.db              # Cơ sở dữ liệu SQLite cục bộ phục vụ demo nhanh
│   └── main.py                  # Điểm khởi chạy ứng dụng FastAPI
│
├── frontend/                    # Giao diện người dùng React + Vite
│   ├── src/
│   │   ├── components/          # Các component giao diện dùng chung (Sidebar, Navbar)
│   │   ├── pages/               # Các trang chức năng chính
│   │   │   ├── Overview.jsx     # Tổng quan dashboard, KPI & Hàng đợi phê duyệt (HITL)
│   │   │   ├── ProductInsights.jsx # Chi tiết SKU, lịch sử so sánh giá, biểu đồ và nhãn cô lập
│   │   │   ├── AgentWorkspace.jsx  # Xem chi tiết log suy luận LangGraph & đàm phán email RAG
│   │   │   └── Configuration.jsx  # Cấu hình ngưỡng cảnh báo & Chỉ thị tùy chỉnh cho LLM
│   │   ├── App.jsx              # Định tuyến trang & CSS Tokens chủ đạo
│   │   └── index.css            # Thiết kế giao diện (Dark Mode, Glassmorphism, Neon borders)
│
├── scripts/
│   └── generate_mock_data.py    # Script khởi tạo 200 SKU & 8,400 bản ghi lịch sử giá đối thủ
│
└── README.md                    # Hướng dẫn tổng quan nền tảng dự án
```

---

## 🛠️ 2. Tình Trạng Mã Nguồn Hiện Tại (Current Implementation Status)

Dự án đã được phát triển vượt xa mức boilerplate thông thường. Các cấu phần kỹ thuật nâng cao sau đã được triển khai hoàn tất:

### A. Quy Trình Cào Dữ Liệu Đa Kênh (Scraper Pipeline)
*   **Marketplace (Shopee / Lazada):** Tích hợp SDK `apify-client` để gọi trực tiếp các actor cào dữ liệu từ nền tảng **Apify**, đảm bảo trích xuất đúng trường giá thực tế (Net Price) sau voucher/discount.
*   **Website độc lập (Pharmacity / GrabMart):** Sử dụng thư viện `Crawl4AI` để crawl tài liệu thô dưới dạng markdown, sau đó trích xuất giá tự động.
*   **Trình duyệt ngầm (Hasaki / TikTok Shop):** Tích hợp động cơ **Playwright** trực tiếp tại máy chủ, giả lập trình duyệt Chromium không đầu (headless) cùng các tham số tránh bị bot-detection để vượt qua các trang web kết xuất phía Client-side (CSR).

### B. Chốt Chặn Xác Thực Giá Bất Thường (Anti-Honeypot Safeguards)
*   **Thuật toán xác thực chéo (Cross-Validation):** Khi phát hiện dữ liệu giá cào mới từ đối thủ, hàm `check_price_anomaly` sẽ đối chiếu giá mới này với **trung bình lịch sử 10 lần cào sạch trước đó** của chính đối thủ đó trên SKU tương ứng.
*   **Cô lập dữ liệu lỗi:** Nếu biên độ lệch giá vượt quá **50%** (ví dụ: bẫy giá Honeypot hiển thị giá rẻ bất thường), hệ thống tự động gán nhãn `is_suspicious = True`, **cô lập bản ghi** khỏi phép tính trung bình CPI để tránh làm sai lệch khuyến nghị định giá.
*   **Hiển thị trực quan (Frontend UI):** Trên trang chi tiết sản phẩm, các mức giá lỗi sẽ bị làm mờ, gạch ngang và gắn nhãn **BẤT THƯỜNG (ISOLATED)** kèm chú thích lọc nhiễu rõ ràng.

### C. Đồ Thị Trạng Thái AI Agent (LangGraph & LlamaIndex RAG)
*   **LangGraph Cyclic Workflow:** Vận hành luồng xử lý alert theo đồ thị trạng thái tuần hoàn:
    1.  `margin_analysis`: Phân tích biên lợi nhuận kỳ vọng của Guardian nếu khớp giá bán rẻ nhất của đối thủ.
    2.  `determine_strategy`: Gọi LLM GPT-4o-mini (hoặc Fallback) để ra quyết định: Khớp giá (`match`) nếu biên lợi nhuận còn lại an toàn; hoặc chuyển sang đàm phán (`negotiate`) nếu biên lợi nhuận bị rớt quá sâu.
    3.  `apply_auto_match` / `supplier_negotiation`: Đưa đề xuất khớp giá vào hàng đợi chờ duyệt, hoặc gọi **LlamaIndex RAG** đọc tài liệu chính sách hãng trong [supplier_policies.txt](file:///C:/Users/ADMIN/Desktop/tailieuhoc/STUDYYY/REPO/P3_TRACK-DETAIL-AND-HOSPILALITY/backend/data/knowledge/supplier_policies.txt) soạn thảo tự động email đàm phán giảm chi phí vốn nhập khẩu gửi hãng.

### D. Cơ Chế Phê Duyệt Con Người (Human-in-the-Loop - HITL)
*   Các quyết định hạ giá bán lẻ của Guardian không được tự ý ghi đè vào CSDL bán hàng. AI Agent sẽ tạo đề xuất ở trạng thái `Pending` trong hàng đợi phê duyệt.
*   Category Manager xem xét lý do lập luận của AI, sau đó bấm nút **Duyệt (Approve)** (khi đó CSDL mới cập nhật giá bán mới) hoặc **Từ chối (Reject)** (hủy đề xuất và đóng cảnh báo lệch giá).

### E. Cấu Hình Động & Khả Năng Tự Phục Hồi (Resiliency)
*   **Cấu hình động:** Toàn bộ tham số biên an toàn và các **Chỉ thị Tùy chỉnh (Custom Instructions)** dành cho LLM Agent được lưu trữ tại `config.json` và cập nhật thông qua REST API trên trang cấu hình Frontend.
*   **Chống treo hệ thống:** Khai báo timeout 8 giây cho kết nối LLM kết hợp bộ lọc xử lý cú pháp JSON tự phục hồi (`Self-Healing JSON Parser`) bằng Regex, cam kết hệ thống luôn phản hồi mượt mà ngay cả khi API OpenAI bị nghẽn mạng.

---

## 🚀 3. Hướng Dẫn Vận Hành Hệ Thống Cục Bộ

### Bước 1: Kích hoạt môi trường ảo Python 3.12
Mở terminal PowerShell tại thư mục gốc dự án và chạy:
```powershell
.venv312\Scripts\Activate
```

### Bước 2: Tái khởi tạo CSDL & Dữ liệu mẫu (8,400 bản ghi lịch sử)
Để chuẩn bị dữ liệu sạch cho demo thuyết trình:
```powershell
Remove-Item -Force backend/guardian.db
python scripts/generate_mock_data.py --db
```

### Bước 3: Khởi động FastAPI Backend
Di chuyển vào thư mục `backend` và khởi chạy server:
```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*API sẽ chạy tại: http://localhost:8000. Bạn có thể xem tài liệu API chi tiết tại: http://localhost:8000/docs*

### Bước 4: Khởi động Frontend React (Vite)
Mở một cửa sổ Terminal mới, di chuyển vào thư mục `frontend` và khởi chạy server:
```powershell
cd frontend
npm install   # nếu chạy lần đầu
npm run dev
```
*Giao diện người dùng sẽ chạy tại: http://localhost:3000*

---

## 🏆 4. Các Điểm Cộng "Đáng Giá" Cho Bài Thuyết Trình
1.  **Assortment Advantage:** Xử lý chuẩn Retail Intelligence: Khi đối thủ hết hàng (Out of Stock), hệ thống giữ nguyên giá của Guardian và đưa CPI về `N/A`, không giảm giá bừa bãi để giữ biên lợi nhuận tối đa cho Guardian.
2.  **Anti-Honeypot validation:** AI lọc dữ liệu rác trước khi đưa vào tính CPI và phân tích giá.
3.  **Human-in-the-Loop:** Cơ chế phòng ngừa rủi ro định giá sai gây thất thoát doanh thu của doanh nghiệp.
4.  **LangGraph & Langfuse:** Kiến trúc Agentic tiên tiến nhất hiện nay cho phép theo dõi từng bước lập luận trực quan của mô hình.
