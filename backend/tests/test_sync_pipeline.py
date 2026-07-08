import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.routes.sync import (
    normalize_scraper_item,
    parse_price_to_int,
    select_first_valid_match,
)


def test_parse_price_to_int_accepts_numeric_and_vnd_strings():
    assert parse_price_to_int(428507) == 428507
    assert parse_price_to_int("428.507 đ") == 428507
    assert parse_price_to_int(" 428,507 VND ") == 428507


def test_normalize_scraper_item_maps_shopee_payload_to_internal_schema():
    raw_item = {
        "title": "La Roche-Posay Anthelios XL SPF50+ PA++++ 50ml",
        "price": "428.507 đ",
        "price_before_discount": "450.000 đ",
        "discount_pct": 5,
        "item_id": 580590480,
        "shop_id": 37251700,
        "availability": "InStock",
        "breadcrumb": [
            {"name": "Shopee", "url": "https://shopee.vn/"},
            {"name": "Kem chống nắng", "url": "https://shopee.vn/sunscreen"},
        ],
    }

    normalized = normalize_scraper_item(raw_item, fallback_platform="Shopee")

    assert normalized["platform"] == "Shopee"
    assert normalized["title"] == raw_item["title"]
    assert normalized["current_price"] == 428507
    assert normalized["original_price"] == 450000
    assert normalized["promotion"] == "Giảm 5%"
    assert normalized["sku_platform"] == "580590480"
    assert normalized["hierarchy"] == "Shopee > Kem chống nắng"
    assert normalized["url"] == "https://shopee.vn/sunscreen"
    assert normalized["raw_data"] == raw_item


def test_select_first_valid_match_skips_empty_and_priceless_items():
    results = [
        {},
        {"title": "No price"},
        {"title": "Valid", "current_price": "99.000 VND"},
    ]

    selected = select_first_valid_match(results, fallback_platform="Hasaki")

    assert selected["title"] == "Valid"
    assert selected["current_price"] == 99000
