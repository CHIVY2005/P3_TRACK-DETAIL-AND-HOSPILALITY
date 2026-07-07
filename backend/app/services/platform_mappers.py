def map_shopee_data(raw_json):
    # Lấy object đầu tiên trong mảng JSON
    item = raw_json[0] 
    
    # 1. Trích xuất giá và khuyến mãi
    current_price = item.get("price")
    original_price = item.get("price_before_discount")
    discount_pct = item.get("discount_pct")
    promotion = f"Giảm {discount_pct}%" if discount_pct else None
    
    # 2. Xử lý Phân cấp sản phẩm (Breadcrumbs)
    breadcrumbs = item.get("breadcrumb", [])
    hierarchy = " > ".join([b.get("name") for b in breadcrumbs]) if breadcrumbs else None
    
    # 3. Lấy URL sản phẩm
    if breadcrumbs:
        url = breadcrumbs[-1].get("url")
    else:
        url = f"https://shopee.vn/product/{item.get('shop_id')}/{item.get('item_id')}"
        
    # 4. Trả về đúng Data Schema nội bộ của Guardian
    mapped_data = {
        "platform": "Shopee",
        "title": item.get("title"),
        "current_price": current_price,
        "original_price": original_price,
        "promotion": promotion,
        "sku_platform": str(item.get("item_id")), # Dùng ID này để map với Barcode nội bộ
        "hierarchy": hierarchy,
        "url": url,
        "stock_status": item.get("availability"),
        "rating": item.get("rating_star")
    }
    
    return mapped_data

# Ví dụ khi chạy:
# print(map_shopee_data(shopee_raw_json))