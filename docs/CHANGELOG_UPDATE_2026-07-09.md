# Changelog Update - 2026-07-09

Tai lieu nay tong hop cac thay doi da duoc thuc hien trong repo de dua MVP hien tai tien gan hon toi flow hackathon va kien truc agent backend da mo ta trong docs.

## 1. Tai cau truc backend theo agent folders

Da dua logic agent ve cau truc ro rang theo tung vai tro:

- `backend/app/agents/market_observer/`
- `backend/app/agents/margin_guardian/`
- `backend/app/agents/supplier_negotiator/`
- `backend/app/agents/orchestrator/`
- `backend/app/agents/shared/`

Ben trong moi agent, file duoc dat ten theo chuc nang thay vi de logic gom chung:

- `*_agent.py`: dieu phoi workflow cua agent
- `*_tools.py`: tap hop rule/tool phu tro cho agent
- `shared/runtime_support.py`: logging, tool event, Langfuse helpers

`backend/app/services/agent_engine.py` hien dong vai tro compatibility layer de goi sang orchestrator moi.

## 2. Tich hop huong code tu nhanh crawl/data branch vao MVP hien tai

Da dua vao nhanh hien tai cac thanh phan de xu ly bai toan ingestion + discovery + crawling:

- Them model `CompetitorLink` trong `backend/app/db/models.py`
- Them `backend/app/services/data_ingestion.py`
- Them `backend/app/services/link_discovery.py`
- Them `backend/app/services/platform_mappers.py`
- Them route `backend/app/routes/sync.py`
- Cap nhat `backend/app/scraper/scraper_engine.py` de:
  - tim link doi thu theo san pham
  - fallback sang discovery neu chua co link
  - map raw payload tu platform ve schema noi bo

Ket qua la luong xu ly da ho tro:

1. Nhan du lieu CSV/JSON noi bo
2. Tu dong map vao schema Postgres
3. Tao `CompetitorLink` neu file nguon da co URL doi thu
4. Neu chua co URL, he thong tao search-driven link discovery
5. Scrape ket qua va chuan hoa ve mot schema thong nhat

## 3. Chuyen supplier negotiator tu RAG sang rule-based/template

Theo huong yeu cau khong phu thuoc RAG pricing logic:

- Bo truy van chinh sach theo RAG trong `shared/runtime_support.py`
- `supplier_negotiator_tools.py` sinh policy context theo template/rule
- `supplier_negotiator_agent.py` dung policy context de draft mail dam phan
- Doi key payload tu `rag_context` sang `policy_context` de phan anh dung logic hien tai

Trang thai hien tai:

- Khong can vector retrieval de ra de xuat dam phan
- Agent supplier co the chay thuần rule-based/template
- RAG khong con la dependency bat buoc cua workflow pricing de demo

## 4. Bo sung scheduler chay dinh ky 1 ngay

Da bo sung runtime va scheduler de agent co the tu dong chay theo chu ky:

- Them `backend/app/services/agent_runtime.py`
- Them `backend/app/services/daily_scheduler.py`
- Cap nhat `backend/app/main.py` de start/stop scheduler theo lifecycle app
- Them endpoint `GET /api/v1/agent/runtime-status`

Config hien tai trong `backend/app/config.py`:

- `AGENT_SCHEDULER_ENABLED = True`
- `AGENT_SCHEDULE_INTERVAL_SECONDS = 86400`

Y nghia:

- Moi 1 ngay he thong tu dong queue 1 lan chay agent
- Lan chay scheduler co the refresh market data va sinh de xuat moi
- Neu da co 1 run dang chay, scheduler se bo qua tick de tranh chong cheo

## 5. Nang cap Langfuse tracing cho project nay

Da tich hop Langfuse theo huong phu hop voi codebase hien tai:

### Cau hinh

- `.env` da duoc cap nhat cho project nay voi bien Langfuse cloud
- `runtime_support.py` da dong bo `LANGFUSE_HOST` va `LANGFUSE_BASE_URL`
- Them check credential hop le truoc khi khoi tao client
- Cache client/callback bang `lru_cache`

### Instrumentation da co

- Trace tool-level trong `run_agent_tool(...)`
- Span cho `pricing-agent-run` trong orchestrator
- Span cho `pricing-alert-run` trong `margin_guardian_agent.py`

### Instrumentation moi vua bo sung

- Them `flush_langfuse()` trong `backend/app/agents/shared/runtime_support.py`
- `backend/app/services/agent_runtime.py` da tao runtime span `agent-runtime-run`
  - ghi nhan `task_id`
  - ghi nhan `source` (`manual` / `scheduler`)
  - ghi nhan `refresh_market_data`
  - flush trace khi ket thuc run
- `backend/app/routes/agent.py`
  - trace request manual run bang span `agent-run-request`
  - trace action approve bang span `agent-action-approve`
  - trace action reject bang span `agent-action-reject`

### Xac thuc key

Da kiem tra truc tiep `client.auth_check()` voi cau hinh Langfuse cua project va nhan ve ket qua hop le.

## 6. Cap nhat docs giai thich kien truc

Da viet lai/cap nhat cac file markdown chinh de giai thich kien truc va flow:

- `README.md`
- `CODEBASE_GUIDE.md`
- `TECHNICAL_EXPLANATION.md`
- `docs/CONFIG_AND_DEPLOY_GUIDE.md`
- `docs/pitch_deck_draft.md`

Noi dung docs hien tap trung vao:

- flow ingestion CSV/JSON
- flow link discovery khi thieu URL doi thu
- flow scraper + fallback + mapper
- flow margin guardian + supplier negotiator
- scheduler hang ngay
- cach van hanh MVP theo nhu cau pitch/demo

## 7. Cap nhat UI/UX frontend

Da co dot cap nhat giao dien lon cho frontend:

- `frontend/src/App.jsx`
- `frontend/src/index.css`
- `frontend/src/pages/Overview.jsx`
- `frontend/src/pages/ProductInsights.jsx`
- `frontend/src/pages/AgentWorkspace.jsx`
- `frontend/src/pages/Configuration.jsx`

Huong cap nhat:

- dua dashboard ve bo cuc agent-ops ro rang hon
- tach khu tong quan, product insight, workspace, config
- chinh lai API base mac dinh theo backend `127.0.0.1:8001`

Luu y:

- Frontend da duoc refactor UI nhung build/serve van can xac minh them trong moi truong local vi truoc do gap van de sandbox/esbuild permission.

## 8. Trang thai MVP hien tai

MVP hien tai da co du cac lop cot loi sau:

- import du lieu noi bo linh hoat
- quan ly link doi thu
- scrape va fallback khi ket noi cloud bi chan
- sinh alert va de xuat agent
- rule-based supplier negotiation
- scheduler tu dong chay hang ngay
- tracing qua Langfuse
- docs kien truc de giai trinh

## 9. Viec nen lam tiep theo

Nhung buoc tiep theo hop ly nhat:

1. Chay test E2E voi backend + DB + scheduler trong docker/local
2. Verify trace hierarchy tren Langfuse UI sau 1 manual run va 1 scheduler run
3. Hoan thien frontend build/runtime trong moi truong hien tai
4. Neu can demo manh hon, them lich su recommendation theo ngay de hien tren dashboard

## 10. Kiem chuan sau cap nhat

Da thuc hien 1 manual backend run tren local API:

- backend start thanh cong tai `127.0.0.1:8001`
- `POST /api/v1/agent/run` tra task moi thanh cong
- runtime status ket thuc sach, khong co `last_error`
- agent task hoan thanh trang thai `Completed`

Sau lan verify nay, da phat hien va sua them 1 diem lech kien truc:

- `margin_guardian_agent.py` truoc do van thu goi LLM roi moi fallback
- da bo hoan toan nhanh LLM nay de module quyet dinh gia tro thanh thuần rule-based nhu docs va yeu cau de bai

## 11. Sua loi tracing Langfuse va xac minh tren cloud

Da sua cac diem co the lam trace khong hien tren Langfuse web:

- bo viec dung `auth_check()` de gate runtime client trong `runtime_support.py`
  - truoc do neu startup gap loi mang tam thoi thi client bi cache `None`
  - ket qua la ca phien app mat tracing du credential van dung
- bo sung `shutdown_langfuse()` va goi trong FastAPI shutdown lifecycle
- bo sung `last_trace_id` va `last_trace_url` vao runtime status de co the doi chieu nhanh voi Langfuse UI
- bo sung script `backend/scripts/verify_langfuse_tracing.py`
- bo sung parser trong `config.py` de chiu duoc gia tri `.env` co inline comment cho cac threshold

Da xac minh outbound thanh cong voi 1 trace that tren Langfuse Cloud:

- trace id: `b0f08afcaf4cd77341032209d2903fe7`
- trace name: `agent-runtime-run`
- trace URL duoc runtime tra ve thanh cong
- truy van lai trace bang Langfuse API thanh cong sau khi flush

## 12. Bo sung explainability cho agent va UI

Da bo sung lop giai thich co cau truc de dung voi brief `reasoning trace` va `human-in-the-loop`:

- `pricing-alert-run` trong Langfuse gio co them `decision_summary`
  - `strategy`
  - `reason`
  - `competitor_name`
  - `guardian_price`
  - `competitor_price`
  - `current_margin_pct`
  - `margin_if_matched_pct`
  - `price_gap_pct`
- `Agent Workspace` tren frontend gio co them khu `Reasoning & trace`
  - link mo truc tiep Langfuse trace tu `last_trace_url`
  - danh sach cac case uu tien voi:
    - rationale
    - strategy
    - gap gia
    - current margin
    - margin if matched
    - recommended action
- `Action queue` va modal supplier draft gio mang theo `decision_summary`
  - operator co the doc ly do de xuat ngay tai noi approve / reject
  - khong can suy nguoc tu logs thuan van ban nua

Muc tieu la de operator khong chi thay action, ma con thay ro vi sao agent de xuat action do.
