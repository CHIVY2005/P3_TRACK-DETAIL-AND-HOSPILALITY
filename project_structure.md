# Bản đồ Cấu trúc Dự án hiện tại

Cây thư mục dưới đây phản ánh workspace sau khi đã dọn rác ở cấp root.

```text
Guardian Pricing Platform/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── mapping_config.json
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── routes/
│   │   │   ├── agent.py
│   │   │   ├── alerts.py
│   │   │   ├── ingest.py
│   │   │   ├── pricing.py
│   │   │   ├── products.py
│   │   │   ├── scraper.py
│   │   │   └── sync.py
│   │   ├── services/
│   │   │   ├── agent_engine.py
│   │   │   ├── ai_matcher.py
│   │   │   ├── apify_client.py
│   │   │   ├── cpi_calculator.py
│   │   │   ├── link_discovery.py
│   │   │   ├── platform_mappers.py
│   │   │   └── scrapers/
│   │   │       ├── base.py
│   │   │       ├── factory.py
│   │   │       └── strategies/
│   │   │           ├── grabmart.py
│   │   │           ├── hasaki.py
│   │   │           └── shopee.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── data/
│   │   └── apify_fallback_fixture.json
│   ├── guardian.db
│   ├── requirements.txt
│   └── tests/
│       └── test_sync_pipeline.py
├── docs/
│   ├── 260704_mission.pdf
│   ├── P3.pdf
│   ├── dashboard_preview.png
│   ├── pitch_deck_draft.md
│   ├── seed_data.pdf
│   └── ĐẶC TẢ BÀI TOÁN HACKATHON.pdf
├── frontend/
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── main.jsx
│   │   └── pages/
│   │       ├── AgentWorkspace.jsx
│   │       ├── Configuration.jsx
│   │       ├── Overview.jsx
│   │       └── ProductInsights.jsx
│   └── vite.config.js
├── mock_data/
│   └── guardian_master_sku.csv
├── promptai/
│   ├── 1. Discussion on strategic direction.txt
│   ├── 2. Discussion on problem-solving.txt
│   ├── 3. Vice Code.txt
│   ├── 4. Session Reset.txt
│   ├── 5. Context Restoration.txt
│   ├── System Role & Context Anchor.txt
│   ├── Token-Saving Instructions.txt
│   └── khám sức khỏe.txt
├── scripts/
│   ├── generate_mock_data.py
│   ├── test_backend.py
│   └── test_matching_agent.py
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── Guidelines for the acceptance of the data collection system.md
├── intervention_required.md
├── phase1_readiness_report.md
├── requirements.txt
├── TECHNICAL_EXPLANATION.md
├── test_execution_report.md
└── virtual_enviroment.md
```

Ghi chú:
- Các file dữ liệu JSON/CSV dư thừa ở root đã được dọn.
- File CSV gốc phục vụ nghiệm thu vẫn nằm tại `mock_data/guardian_master_sku.csv`.
- Cấu hình fallback Apify/fixture vẫn được giữ nguyên trong `backend/app/config.py`.
