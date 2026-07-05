# GUARDIAN - Real-Time Pricing Intelligence & AI Agent Platform

Đây là bộ mã nguồn Boilerplate (Khung dự án chuẩn) phục vụ cho cuộc thi AI Hackathon. Hệ thống tích hợp khả năng giám sát giá đa kênh thời gian thực (Shopee, Lazada, TikTok Shop, GrabMart) đối với Top 200 SKU và vận hành **AI Pricing Agent** tự động để tối ưu hóa biên lợi nhuận.

---

## 🚀 Tính Năng Nổi Bật

1.  **Single Source of Truth Database:** Cơ sở dữ liệu SQLite cục bộ được thiết lập sẵn, tự động khởi tạo bảng mà không cần cấu hình phức tạp.
2.  **Competitor Pricing Index (CPI):** Chỉ số so sánh giá chuẩn hóa ($CPI = \frac{Price_{Guardian}}{Price_{Competitor}} \times 100$) giúp phát hiện sản phẩm bị ép giá hoặc cơ hội tăng giá.
3.  **Bóc Tách Giá Thực Tế (Net Price):** Xử lý chiết khấu, voucher và cơ chế chạy khuyến mãi để có giá net thực tế của đối thủ.
4.  **Agentic AI Pricing Optimizer:** Vòng lặp tự động **Perceive (Cảnh báo) -> Reason (Phân tích giá vốn & biên lợi nhuận) -> Act (Thực thi)**:
    *   *Tool Match Giá:* Tự động giảm giá trên sàn nếu biên lợi nhuận đạt mức an toàn (>15%).
    *   *Tool Đàm phán:* Soạn sẵn thư điện tử thương lượng giảm giá vốn gửi Supplier nếu biên lợi nhuận bị đe dọa.
5.  **Dashboard Cao Cấp:** Giao diện tối màu (Premium Dark Mode) trực quan hiển thị biểu đồ xu hướng Recharts và bảng điều khiển logs hoạt động của AI Agent thời gian thực.

---

## 📁 Cấu Trúc Thư Mục

```text
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── db/               # SQLAlchemy Session & Models
│   │   ├── routes/           # API Endpoints (Products, Alerts, Scraper, Agent)
│   │   ├── services/         # CPI Calculator, Agent Loop Engine
│   │   ├── scraper/          # Scraper skeleton & Mock algorithms
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── config.py         # Cấu hình môi trường (SQLite/PostgreSQL)
│   │   └── main.py           # Entrypoint khởi tạo FastAPI
│   └── requirements.txt      # Thư viện Python yêu cầu
├── frontend/                 # React + Vite Client
│   ├── src/
│   │   ├── pages/            # Overview, ProductInsights, AgentWorkspace, Configuration
│   │   ├── App.jsx           # Main routing & state
│   │   ├── index.css         # Custom Premium CSS Variables & Styles
│   │   └── main.jsx          # Entrypoint React
│   ├── package.json          # npm packages
│   └── vite.config.js        # Vite config
├── scripts/                  # Công cụ & Kịch bản bổ trợ
│   ├── generate_mock_data.py # Tạo 200 SKU & Seed CSDL
│   └── test_backend.py       # Kiểm thử API Endpoints tự động
├── docs/                     # Tài liệu & Pitch Deck dàn ý
├── docker-compose.yml        # PostgreSQL & Redis container setup (Tùy chọn)
└── .env                      # Cấu hình biến môi trường
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy Dự Án

### 1. Cài đặt Backend & Khởi tạo Dữ liệu
Mở Terminal tại thư mục gốc của dự án:

```bash
# 1. Tạo môi trường ảo Python
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Trên Windows:
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate

# 3. Cài đặt các thư viện
pip install -r backend/requirements.txt

# 4. Tạo dữ liệu giả lập & Seed vào Database SQLite (guardian.db)
python scripts/generate_mock_data.py --db

# 5. Khởi chạy Backend Server
cd backend
uvicorn app.main:app --reload
```
API Docs sẽ có sẵn tại: `http://localhost:8000/docs`

### 2. Cài đặt & Chạy Frontend Dashboard
Mở cửa sổ Terminal mới:

```bash
cd frontend
npm install
npm run dev
```
Truy cập giao diện tại: `http://localhost:3000`

### 3. Kiểm thử API tự động
Bạn có thể kiểm tra xem các API có hoạt động đúng không bằng cách chạy:
```bash
python scripts/test_backend.py
```

---

## 🤖 Cách Hoạt Động của AI Agent (Vòng Lặp Độc Lập)

Khi Category Manager bấm **"Kích hoạt Pricing Agent"** từ giao diện:
1.  Agent quét các `Alert` đang kích hoạt (do giá đối thủ giảm sâu hoặc lệch CPI).
2.  Với mỗi cảnh báo, Agent tính toán:
    *   Gọi tool `calculate_margin()` để xem mức biên lợi nhuận của sản phẩm dựa trên **Cost Price (Giá vốn)**.
3.  Ra quyết định:
    *   *Mức biên đạt ngưỡng an toàn (>=15%):* Tự động điều chỉnh giá Guardian xuống ngang đối thủ (`adjust_system_price()`) và giải quyết cảnh báo (`is_resolved=True`).
    *   *Mức biên rớt dưới ngưỡng an toàn (<15%):* Dừng giảm giá, gọi tool `generate_supplier_negotiation_draft()` để soạn sẵn email gửi Supplier yêu cầu giảm giá nhập.
4.  Logs chi tiết luồng suy nghĩ (Thoughts), quan sát (Observations) và hành động (Actions) được đẩy lên Dashboard dạng Terminal trực quan.

---

## 🧠 Vai Trò Của AI Agent Trong Hệ Thống (Agent Roles)

Trong nền tảng **GUARDIAN**, AI Pricing Agent đóng vai trò cốt lõi, thay thế các quy trình nghiệp vụ thủ công phức tạp bằng chuỗi hành vi thông minh tự trị (Autonomous Agentic Workflows):

1.  **Market Observer (Giám sát & Phát hiện Bất thường):**
    *   *Vai trò:* Theo dõi liên tục biến động giá Net Price của toàn bộ Top 200 SKU trên các kênh Shopee, Lazada, TikTok Shop, GrabMart.
    *   *Hành vi:* Phát hiện lập tức các hành vi phá giá của đối thủ hoặc cơ hội tăng giá của Guardian khi đối thủ hết hàng/tăng giá, tự động kích hoạt cảnh báo tương ứng với mức độ nghiêm trọng (High, Medium, Low).

2.  **Margin Guardian (Bảo vệ Biên lợi nhuận):**
    *   *Vai trò:* Là chốt chặn bảo mật an toàn tài chính của doanh nghiệp.
    *   *Hành vi:* Thay vì tự động giảm giá mù quáng theo đối thủ để cạnh tranh (dẫn đến chiến tranh giá phá hủy biên lợi nhuận), Agent luôn đối chiếu giá đối thủ với **Cost Price (Giá vốn)** của sản phẩm để bảo vệ biên lợi nhuận tối thiểu được quy định trong cấu hình (mặc định là 15%).

3.  **Autonomous Decision-Maker (Quyết định Điều phối):**
    *   *Vai trò:* Phân tích đa chiều và đưa ra phương án xử lý tối ưu.
    *   *Hành vi:* Sử dụng các quy tắc nghiệp vụ kết hợp suy luận để phân loại sản phẩm và quyết định: khi nào nên **Auto-Match giá** để chiếm lĩnh thị phần, khi nào nên **Maintain giá** để bảo toàn lợi nhuận, và khi nào nên **Yêu cầu hỗ trợ giá nhập**.

4.  **Supplier Negotiator (Đàm phán viên ảo):**
    *   *Vai trò:* Hỗ trợ Category Manager soạn thảo đàm phán với nhà cung cấp.
    *   *Hành vi:* Khi giá bán của đối thủ giảm xuống dưới mức giá vốn an toàn của Guardian, Agent sẽ tự động soạn thảo email đề xuất đàm phán (Purchase Cost Rebates) gửi nhà cung cấp dựa trên thông tin nhà sản xuất của sản phẩm đó, giúp doanh nghiệp đạt được chi phí nhập rẻ hơn mà không cần Category Manager ngồi viết email thủ công cho từng nhà cung cấp.

