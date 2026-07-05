# Pitch Deck Framework: AI-powered Pricing Intelligence Platform (GUARDIAN)

This document provides a comprehensive structured outline for your hackathon pitch deck. It focuses on demonstrating the business value, technical innovation, and **Agentic AI** capabilities of the **GUARDIAN** pricing command center.

---

## Slide 1: Bối cảnh & Nỗi đau Thị trường (The Problem)
*   **Tiêu đề:** Nỗi đau Định giá Đa kênh: Khi Con Người Đuổi Theo Giá Thị Trường
*   **Vấn đề cốt lõi:**
    *   Guardian thiếu một nguồn dữ liệu đáng tin cậy duy nhất (Single Source of Truth) để giám sát giá đối thủ theo thời gian thực trên Shopee, Lazada, TikTok Shop, GrabMart.
    *   Đội ngũ Thương mại (Commercial teams) mất hàng chục giờ rà soát thủ công mỗi tuần để khớp giá, bóc tách voucher, combo khuyến mãi của đối thủ.
    *   **Hậu quả:** Mất thị phần do phản ứng chậm (overpriced) hoặc rò rỉ biên lợi nhuận do điều chỉnh giá cảm tính (underpriced).
*   **Hình ảnh gợi ý:** Biểu đồ thể hiện sự phức tạp của cơ cấu giá đa kênh (Raw price vs Discount vs Voucher vs Net price) và biểu tượng thể hiện sự quá tải của đội ngũ CM.

---

## Slide 2: Giải pháp GUARDIAN (The Solution)
*   **Tiêu đề:** GUARDIAN Pricing Command Center - Trí tuệ Định giá Đa kênh
*   **Giải pháp:** Nền tảng tự động giám sát, tính toán và so sánh giá thời gian thực cho Top 200 SKU trọng điểm.
*   **Đặc điểm nổi bật:**
    *   **Net Price Intelligence:** Tự động bóc tách các cơ chế giá phức tạp (voucher tích lũy, livestream voucher, flash sales) để tìm ra mức giá thực tế đối thủ đang bán.
    *   **Competitor Pricing Index (CPI):** Chỉ số chuẩn hóa giúp nhìn thấy ngay lập tức sức mạnh cạnh tranh giá theo từng kênh hoặc toàn sàn.
*   **Hình ảnh gợi ý:** Ảnh chụp màn hình Dashboard Overview với các chỉ số lớn (CPI, SKU bị ép giá, cơ hội tăng giá).

---

## Slide 3: Điểm Nhấn Công Nghệ: Agentic AI Tự Quyết (The AI Agent)
*   **Tiêu đề:** Vượt Lên Trên Chatbot: AI Agent Tự Động Tối Ưu Lợi Nhuận
*   **Sự khác biệt:** Không phải là chatbot hỏi đáp thông thường. Hệ thống tích hợp một **AI Pricing Agent** tự động vận hành theo vòng lặp đóng (Perceive -> Reason -> Act):
    *   **Perceive:** Tự động phát hiện các cảnh báo lệch giá (CPI ngoài vùng an toàn).
    *   **Reason:** Sử dụng quy tắc nghiệp vụ & mô hình suy luận kiểm tra biên lợi nhuận thực tế dựa trên **Cost Price (Giá vốn)**.
    *   **Act (Sử dụng công cụ):**
        *   *Công cụ Match Giá:* Tự động giảm giá bán của Guardian trên hệ thống nếu biên lợi nhuận sau giảm vẫn đạt mục tiêu (>15%).
        *   *Công cụ Đàm phán:* Nếu biên lợi nhuận rớt dưới mức an toàn, Agent tự động soạn thư đề xuất đàm phán giảm giá nhập (purchase cost protection) gửi đến nhà cung cấp.
*   **Hình ảnh gợi ý:** Sơ đồ luồng tư duy và công cụ của AI Agent (vòng lặp suy nghĩ và thực thi hành động).

---

## Slide 4: Kết Quả & Giá Trị Kinh Doanh (Expected Outcomes)
*   **Tiêu đề:** Tối Ưu Biên Lợi Nhuận - Tiết Kiệm 95% Công Sức Vận Hành
*   **Tác động thực tế:**
    *   **Giảm 90%+** công sức rà soát giá thủ công của Category Managers.
    *   **Tăng tốc độ phản ứng:** Khớp giá đối thủ hoặc nắm bắt cơ hội tăng giá trong vòng vài phút thay vì vài ngày.
    *   **Bảo vệ biên lợi nhuận:** Ngăn chặn việc chạy đua vũ trang giảm giá mù quáng nhờ chốt chặn an toàn Margin-Limit của Agent.
*   **Hình ảnh gợi ý:** Biểu đồ so sánh thời gian phản ứng giá và sự tăng trưởng biên lợi nhuận trước và sau khi áp dụng GUARDIAN.

---

## Slide 5: Kế hoạch Phát triển & Demo (Roadmap & Live Demo)
*   **Tiêu đề:** Live Demo & Lộ Trình Mở Rộng
*   **Demo thực tế:** Chỉ vào AI Agent Terminal đang chạy thực tế, cho thấy các Tool Calls (margin calculator, adjust price, draft email) được thực thi trực quan.
*   **Roadmap:**
    *   *Giai đoạn 1:* Tích hợp sâu API Shopee/Lazada chính hãng và hệ thống ERP nội bộ Guardian.
    *   *Giai đoạn 2:* Áp dụng mô hình Học Máy dự đoán phản ứng doanh số khi thay đổi giá (Elasticity Pricing Model).
    *   *Giai đoạn 3:* Tự động hóa gửi email đàm phán đến Supplier qua hệ thống CRM kết nối.
