from datetime import datetime, timedelta, timezone

import pytest

from app.db import models
from app.services.channel_intelligence import build_channel_intelligence


def test_channel_cpi_uses_latest_clean_price_per_sku(db_session):
    products = [
        models.Product(
            barcode="A001",
            name="Product A",
            category="Skincare",
            guardian_price=100_000,
            cost_price=60_000,
        ),
        models.Product(
            barcode="A002",
            name="Product B",
            category="Skincare",
            guardian_price=100_000,
            cost_price=60_000,
        ),
    ]
    db_session.add_all(products)
    db_session.flush()

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            models.CompetitorPrice(
                product_id=products[0].id,
                competitor_name="Shopee",
                raw_price=120_000,
                net_price=120_000,
                scraped_at=now - timedelta(days=1),
            ),
            models.CompetitorPrice(
                product_id=products[0].id,
                competitor_name="Shopee",
                raw_price=100_000,
                discount=20_000,
                net_price=80_000,
                voucher_details="Voucher 10k",
                promo_mechanics="Flash Sale",
                scraped_at=now,
            ),
            models.CompetitorPrice(
                product_id=products[1].id,
                competitor_name="Shopee",
                raw_price=200_000,
                net_price=200_000,
                promo_mechanics="Combo buy 2",
                scraped_at=now,
            ),
            models.CompetitorPrice(
                product_id=products[0].id,
                competitor_name="Lazada",
                raw_price=90_000,
                net_price=90_000,
                stock_status="OUT_OF_STOCK",
                scraped_at=now,
            ),
        ]
    )
    db_session.commit()

    result = build_channel_intelligence(db_session)
    shopee = next(row for row in result["channels"] if row["channel"] == "Shopee")
    lazada = next(row for row in result["channels"] if row["channel"] == "Lazada")

    assert shopee["cpi"] == pytest.approx(87.5)
    assert shopee["sku_coverage"] == 2
    assert shopee["coverage_pct"] == 100.0
    assert shopee["promotion_sku"] == 2
    assert shopee["voucher_sku"] == 1
    assert shopee["bundle_sku"] == 1
    assert shopee["flash_sale_sku"] == 1
    assert lazada["sku_coverage"] == 0
    assert lazada["observation_coverage_pct"] == 50.0
    assert result["summary"]["observed_sku"] == 2
    assert result["summary"]["channels_with_data"] == 2
