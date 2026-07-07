# Bản đồ Cấu trúc Dự án (Project Structure Map)

Dưới đây là cấu trúc thư mục dự án "Guardian Pricing Platform", đã được lược bỏ các thư mục hệ thống và rác như `node_modules`, `venv`, `__pycache__`, `.git`, v.v. để tối ưu hiển thị.

```text
P3_TRACK-DETAIL-AND-HOSPILALITY/
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   ├── models.py - Định nghĩa các schema CSDL bằng SQLAlchemy (Products, CompetitorPrice, PricingIndex, Alert, Agent).
│   │   │   └── session.py - Quản lý kết nối tới CSDL.
│   │   ├── routes/
│   │   │   ├── agent.py - File API xử lý luồng hoạt động của AI Agent Workspace.
│   │   │   ├── alerts.py - File API quản lý các cảnh báo giá (alerts).
│   │   │   ├── pricing.py - File API xử lý logic định giá & tính toán chỉ số CPI.
│   │   │   ├── products.py - File API để lấy thông tin và quản lý sản phẩm nội bộ (Guardian).
│   │   │   └── scraper.py - File API điều khiển luồng cào dữ liệu đối thủ (Scraper Controls).
│   │   ├── scraper/
│   │   │   └── mock_scraper.py
│   │   ├── services/
│   │   │   ├── agent_engine.py
│   │   │   ├── cpi_calculator.py
│   │   │   └── platform_mappers.py
│   │   ├── config.py - Quản lý các cài đặt cấu hình dự án (Project settings).
│   │   ├── main.py - Điểm khởi chạy của FastAPI backend, cài đặt CORS và đăng ký các routes API.
│   │   └── schemas.py
│   └── requirements.txt
├── data/
│   ├── competitor_scraped_data.csv
│   └── guardian_internal_sku.csv
├── docs/
│   ├── 260704_mission.pdf
│   ├── P3.pdf
│   ├── pitch_deck_draft.md
│   └── ĐẶC TẢ BÀI TOÁN HACKATHON.pdf
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AgentWorkspace.jsx
│   │   │   ├── Configuration.jsx
│   │   │   ├── Overview.jsx
│   │   │   └── ProductInsights.jsx
│   │   ├── App.jsx - Component chính của React (Router & Sidebar), theo dõi trạng thái hệ thống theo thời gian thực (Scraper, Agent).
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json - Chứa khai báo thư viện frontend.
│   └── vite.config.js - Cấu hình máy chủ Vite cho frontend, chạy ở cổng 3000.
├── scripts/
│   ├── generate_mock_data.py
│   └── test_backend.py
├── .env.example
├── .gitignore
├── README.md
├── dataset_shopee-scraper_*.json
├── docker-compose.yml - Định nghĩa các services container, bao gồm Postgres database và Redis.
├── generate_mockdata.py
├── requirements.txt
├── test_targets.json
└── virtual_enviroment.md
```
