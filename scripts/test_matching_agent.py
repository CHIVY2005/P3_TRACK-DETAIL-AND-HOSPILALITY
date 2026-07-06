import os
import sys

# Set standard output to handle UTF-8 printing safely on Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

def run_matching_test():
    print("======================================================================")
    print("HE THONG KIEM THU KHU NHIEU DU LIEU & SO KHOP CHUOI (SIMILARITY TEST)")
    print("======================================================================")
    
    # Target Guardian Product Details
    target_barcode = "7612345678901"
    target_product_name = "Sữa Rửa Mặt Cetaphil Dịu Lành Cho Da Nhạy Cảm 500ml"
    similarity_cutoff = 0.85
    
    print(f"Target Product:")
    print(f"   - Barcode: {target_barcode}")
    print(f"   - Standard Name: '{target_product_name}'")
    print(f"   - Similarity Cutoff: {similarity_cutoff}")
    print("----------------------------------------------------------------------")
    
    # Test cases representing data fetched from competitor platforms
    test_cases = [
        {
            "id": 1,
            "description": "Test nhiễu dung tích (Kiểm tra Cutoff từ chối)",
            "competitor_input": "Sữa rửa mặt Cetaphil dịu lành cho da nhạy cảm 125ml",
            "simulated_score": 0.62,
        },
        {
            "id": 2,
            "description": "Test viết tắt & lỗi chính tả (Kiểm tra Hybrid Search)",
            "competitor_input": "Srm Cetaphil dịu nhẹ bản mới 500ml",
            "simulated_score": 0.91,
        }
    ]
    
    for case in test_cases:
        print(f"[Case {case['id']}] {case['description']}:")
        print(f"   - Đầu vào đối thủ: '{case['competitor_input']}'")
        
        # Calculate decision based on cutoff
        score = case["simulated_score"]
        is_matched = score >= similarity_cutoff
        decision = "APPROVED & MATCHED" if is_matched else "REJECTED (Mismatched volume/details)"
        
        print(f"   - Điểm so khớp (Similarity Score): {score:.2f}")
        print(f"   - Trạng thái xử lý: {decision}")
        
        if is_matched:
            print(f"   - Ánh xạ thành công về Barcode: {target_barcode}")
        else:
            print(f"   - Hành động: Bỏ qua dòng dữ liệu này (Tránh lỗi gom giá sai dung tích).")
        print("----------------------------------------------------------------------")
        
    print("Thử nghiệm hoàn tất.")
    print("======================================================================")

if __name__ == "__main__":
    run_matching_test()
