import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta
import os

# Khởi tạo Faker để sinh các chuỗi ngẫu nhiên (dùng locale Tiếng Việt)
fake = Faker('vi_VN')

def generate_mock_data():
    print("⏳ Đang khởi tạo dữ liệu giả lập...")
    
    # ==========================================
    # 0. TẠO THƯ MỤC LƯU TRỮ
    # ==========================================
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Đã kiểm tra/khởi tạo thư mục: '{output_dir}/'")

    # ==========================================
    # 1. TẠO FILE DỮ LIỆU NỘI BỘ (guardian_internal_sku.csv)
    # ==========================================
    num_skus = 200
    categories = ['Skincare', 'Bodycare', 'Healthcare', 'Makeup']
    promotions = ["Không", "Giảm 10%", "Giảm 20K", "Mua 1 tặng 1"]
    
    # Từ khóa để sinh tên sản phẩm mỹ phẩm thực tế
    brands = ["La Roche-Posay", "Cetaphil", "Bioderma", "CeraVe", "Garnier", "Vichy", "L'Oreal", "Maybelline", "Hada Labo", "Innisfree"]
    types = ["Kem chống nắng", "Sữa rửa mặt", "Nước tẩy trang", "Toner", "Serum", "Kem dưỡng ẩm", "Sữa tắm", "Dầu gội", "Mặt nạ", "Kem nền"]
    variants = ["50ml", "100ml", "250ml", "500ml", "30ml", "150g", "200g"]

    guardian_data = []
    for i in range(1, num_skus + 1):
        # Tạo mã nội bộ & barcode 13 số
        sku_id = f"GUA-{1000 + i}"
        barcode = int(''.join([str(random.randint(0, 9)) for _ in range(13)]))
        
        # Sinh tên sản phẩm ngẫu nhiên nhưng có ý nghĩa
        product_name = f"{random.choice(types)} {random.choice(brands)} {random.choice(variants)}"
        
        # Giá từ 50.000 đến 1.500.000 VNĐ (làm tròn đến hàng nghìn)
        current_price = random.randint(50, 1500) * 1000
        
        guardian_data.append({
            "sku_id": sku_id,
            "barcode": barcode,
            "product_name": product_name,
            "category": random.choice(categories),
            "current_price": current_price,
            "promotion_details": random.choice(promotions)
        })

    df_guardian = pd.DataFrame(guardian_data)

    # ==========================================
    # 2. TẠO FILE DỮ LIỆU CÀO ĐỐI THỦ (competitor_scraped_data.csv)
    # ==========================================
    competitor_channels = ['Shopee', 'Lazada', 'TikTok Shop', 'GrabMart']
    vouchers = ["Giảm 15k cho đơn từ 150k", "Freeship extra", "Hoàn xu 10%", "Giảm 50K đơn 300K", ""]
    alterations = ["Chính hãng", "[Freeship]", "Date mới", "Giá sỉ", "Auth 100%"]
    
    competitor_data = []
    scrape_counter = 1
    now = datetime.now()

    # Duyệt qua từng sản phẩm của Guardian để tạo dữ liệu đối thủ tương ứng
    for _, row in df_guardian.iterrows():
        # Mỗi SKU nội bộ có 3-5 dòng dữ liệu đối thủ
        num_competitors = random.randint(3, 5) 
        
        for _ in range(num_competitors):
            scrape_id = f"SCRAPE-{scrape_counter:04d}"
            scrape_counter += 1
            
            # Cố tình làm sai lệch tên sản phẩm một chút để mô phỏng dữ liệu cào thực tế
            if random.random() > 0.5:
                comp_name = f"{random.choice(alterations)} {row['product_name']}"
            else:
                comp_name = f"{row['product_name']} {random.choice(alterations)}"
            
            # Giá gốc dao động +-15% so với giá Guardian
            variation = random.uniform(-0.15, 0.15)
            listed_price = int(row['current_price'] * (1 + variation))
            listed_price = round(listed_price, -3) # Làm tròn hàng nghìn
            
            # Giá giảm phải <= giá gốc (giảm tối đa 30%)
            discount = random.uniform(0, 0.3)
            discounted_price = int(listed_price * (1 - discount))
            discounted_price = round(discounted_price, -3)
            
            # Timestamp trong vòng 7 ngày qua
            random_days = random.uniform(0, 7)
            timestamp = now - timedelta(days=random_days)
            
            competitor_data.append({
                "scrape_id": scrape_id,
                "barcode": row['barcode'], # Đảm bảo map đúng barcode
                "competitor_channel": random.choice(competitor_channels),
                "competitor_product_name": comp_name,
                "listed_price": listed_price,
                "discounted_price": discounted_price,
                "voucher_text": random.choice(vouchers),
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

    df_competitors = pd.DataFrame(competitor_data)

    # ==========================================
    # 3. XUẤT FILE CSV VÀO THƯ MỤC 'data'
    # ==========================================
    guardian_path = os.path.join(output_dir, "guardian_internal_sku.csv")
    competitor_path = os.path.join(output_dir, "competitor_scraped_data.csv")

    df_guardian.to_csv(guardian_path, index=False, encoding='utf-8-sig')
    df_competitors.to_csv(competitor_path, index=False, encoding='utf-8-sig')

    print("✅ Đã tạo và lưu thành công 2 file CSV mock data!")
    print(f"📊 1. {guardian_path}: {len(df_guardian)} dòng")
    print(f"📊 2. {competitor_path}: {len(df_competitors)} dòng")

if __name__ == "__main__":
    generate_mock_data()