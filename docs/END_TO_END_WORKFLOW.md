# GUARDIAN PRICING OS - END-TO-END WORKFLOW

Tài liệu này mô tả cách ứng dụng vận hành từ lúc nhận dữ liệu nội bộ đến khi tạo, phê duyệt và theo dõi một đề xuất giá.

## 1. Luồng tổng thể

```text
CSV/JSON nội bộ
      |
      v
Import, kiểm tra và chuẩn hóa sản phẩm
      |
      v
Tìm hoặc bổ sung link sản phẩm đối thủ
      |
      v
Scheduler hằng ngày hoặc người dùng bấm Refresh market
      |
      v
Thu thập và chuẩn hóa effective price đa kênh
      |
      v
Lưu lịch sử giá và tính CPI
      |
      v
Phát hiện bất thường, tạo pricing alert
      |
      v
Decision cycle chạy rule và kiểm tra margin
      |
      v
Tạo hành động chờ Commercial operator phê duyệt
      |
      v
Approve/Reject, tính lại CPI và lưu audit evidence
```

Vòng lặp kinh doanh của hệ thống là:

> Observe -> Detect -> Recommend -> Guard -> Approve -> Act -> Measure.

## 2. Nạp dữ liệu sản phẩm

Người dùng có thể đưa dữ liệu CSV/JSON chứa barcode, SKU, tên, thương hiệu, giá bán, giá vốn và các thuộc tính liên quan. Dynamic ingestion ánh xạ dữ liệu về schema chung, kiểm tra các trường bắt buộc và ghi vào database bằng SQLAlchemy.

Trong môi trường development/demo/local/test, nếu catalog hoàn toàn rỗng và `AUTO_SEED_DEMO=True`, startup bootstrap nạp bộ dữ liệu demo 200 SKU. Nếu đã có catalog, hệ thống giữ nguyên và không seed đè. Production phải đặt `ENV=production` và nên tắt auto-seed.

## 3. Xác định sản phẩm đối thủ

- Nếu catalog đã có link Shopee, Hasaki, Watsons hoặc kênh khác, hệ thống dùng link đó.
- Nếu chỉ có tên/barcode/thương hiệu, Link Discovery tạo ứng viên tìm kiếm và lưu competitor link.
- Với production, các match có độ tin cậy thấp phải được người dùng xác nhận trước khi dùng cho quyết định giá.

## 4. Thu thập dữ liệu thị trường

Luồng chạy được kích hoạt theo hai cách:

- tự động mỗi 86.400 giây, tương đương một ngày, khi scheduler được bật;
- thủ công bằng nút `Refresh market` trên Pricing Command.

Market Observer chọn connector phù hợp cho từng kênh. Luồng có thể sử dụng Apify, Playwright/Crawl4AI hoặc deterministic fixture fallback. Fallback giúp buổi demo tiếp tục khi mạng hay anti-bot chặn, nhưng phải được gắn nhãn và không được trình bày như dữ liệu real-time.

## 5. Chuẩn hóa và lưu lịch sử giá

Platform mapper chuyển payload của từng nguồn về schema chung:

- giá niêm yết;
- giá sau khuyến mãi hoặc voucher hợp lệ;
- effective price dùng để so sánh;
- tình trạng hàng, rating và thời điểm thu thập;
- dữ liệu nguồn phục vụ kiểm tra và tracing.

Mỗi lần thu thập tạo một observation mới thay vì ghi đè lịch sử. CPI engine sử dụng observation sạch và mới nhất của từng kênh.

## 6. CPI và phát hiện bất thường

CPI biểu diễn vị thế giá của Guardian so với giá tham chiếu thị trường:

```text
CPI = Giá Guardian / Giá thị trường tham chiếu
```

- CPI gần `1.00`: giá gần ngang thị trường.
- CPI cao hơn ngưỡng: có nguy cơ kém cạnh tranh.
- CPI thấp nhưng margin yếu: có nguy cơ bán quá rẻ.
- Giá hoặc promotion thay đổi bất thường: tạo alert để kiểm tra.

## 7. Decision cycle và các agent

- **Market Observer** cung cấp bằng chứng thị trường và freshness.
- **Margin Guardian** tính margin hiện tại và các kịch bản giá.
- **Supplier Negotiator** tạo template đề nghị hỗ trợ từ nhà cung cấp khi không thể giảm giá an toàn.
- **Orchestrator** phối hợp các bước và tạo decision summary.

Pricing hiện dùng rule-based/template, không dùng RAG hoặc LLM để tự suy diễn chính sách giá:

```text
Nếu Guardian đắt hơn đối thủ
và giá đề xuất vẫn đạt margin floor
=> tạo đề xuất price alignment.

Nếu price alignment làm margin thấp hơn floor
=> giữ giá và tạo supplier-support draft.

Nếu dữ liệu thiếu, cũ hoặc độ tin cậy thấp
=> chuyển sang kiểm tra thủ công.
```

## 8. Human approval

Decision Desk hiển thị giá hiện tại, giá đề xuất, CPI, margin trước/sau, nguồn dữ liệu, rule được kích hoạt và evidence liên quan. Người phụ trách chọn Approve hoặc Reject.

MVP không tự ý đổi giá trên hệ thống bán hàng bên ngoài. Khi có tích hợp production, hành động đã duyệt có thể được đẩy sang PIM, ERP hoặc pricing API.

## 9. Langfuse tracing

Các run quan trọng được ghi thành trace/span/tool observation, ví dụ:

```text
market-refresh
  +-- scrape-channel
  +-- normalize-price
  +-- calculate-cpi
  +-- create-alert

pricing-alert-run
  +-- compute-margin-scenarios
  +-- select-rule
  +-- create-action
  +-- adjust-system-price
```

Langfuse dùng để kiểm tra input/output, latency, lỗi, tool events và decision evidence. Hệ thống không lưu hoặc hiển thị chain-of-thought bí mật; phần giải thích là dữ liệu có cấu trúc, có thể kiểm toán.

## 10. Tại sao không cài PostgreSQL vẫn lưu được dữ liệu?

Mặc định cấu hình có:

```env
USE_SQLITE=True
SQLITE_DB_PATH=
```

Khi `USE_SQLITE=True`, `backend/app/config.py` tạo connection URI trỏ đến:

```text
backend/guardian.db
```

SQLite là database nhúng. Nó đọc và ghi trực tiếp vào một file thông qua thư viện đi kèm Python/SQLAlchemy, vì vậy không cần cài database server, tạo service, mở cổng 5432 hay chạy Docker PostgreSQL. Dữ liệu vẫn còn sau khi backend restart vì được lưu trên ổ đĩa trong `guardian.db`, không nằm trong RAM.

File database không được commit lên Git. Vì vậy máy clone mới sẽ tạo database riêng; startup bootstrap có thể nạp demo data nếu catalog đang rỗng.

## 11. Khi nào dùng SQLite, khi nào dùng PostgreSQL?

| Tiêu chí | SQLite | PostgreSQL |
|---|---|---|
| Phù hợp | Local development, demo, chấm thi | Pilot và production |
| Cài đặt | Không cần database server | Cần server hoặc Docker/cloud database |
| Concurrent writes | Hạn chế | Tốt hơn cho nhiều worker/user |
| Mở rộng | Một backend process, dữ liệu vừa phải | Scheduler/worker queue và tải lớn |
| Availability/backup | Sao lưu file thủ công | Có backup, replication và monitoring chuẩn |
| PostgreSQL extensions | Không hỗ trợ | Có thể dùng pgvector và extension khác |

SQLite giúp dự án chạy ngay trên máy giám khảo hoặc máy đồng đội. PostgreSQL vẫn là lựa chọn đúng cho production, đặc biệt khi có nhiều worker crawler, nhiều người duyệt đồng thời, yêu cầu backup/HA hoặc cần pgvector.

## 12. Chuyển sang PostgreSQL

Khởi động PostgreSQL bằng Docker Compose hoặc dùng managed PostgreSQL, sau đó cấu hình:

```env
USE_SQLITE=False
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=guardian_db
```

Sau khi restart backend, SQLAlchemy dùng PostgreSQL URI thay cho file SQLite. Cần thực hiện migration/import dữ liệu nếu muốn chuyển catalog và lịch sử đang có trong `guardian.db`; đổi biến môi trường không tự sao chép dữ liệu cũ.

## 13. Giới hạn cần nói trung thực

- Scraper và link matching hiện là MVP, chưa production-grade cho tải lớn.
- Scheduler chạy trong backend process, chưa phải distributed worker queue.
- Chưa có authentication, role-based approval và audit log production đầy đủ.
- Fixture fallback bảo đảm demo ổn định nhưng không thay thế dữ liệu thị trường thật.
- SQLite phù hợp demo, không phải kiến trúc lưu trữ cuối cùng cho nhiều instance backend.
