import pytest

from app.db import models
from app.services.data_ingestion import import_dataset_from_upload
from app.services.platform_mappers import map_marketplace_result


def test_marketplace_mapper_calculates_effective_price_after_voucher():
    result = map_marketplace_result(
        "Shopee",
        {
            "price_before_discount": "500.000",
            "price": "450.000",
            "voucher_info": "Voucher 20k",
            "promotion_name": "Flash Sale",
            "availability": "InStock",
        },
    )

    assert result["raw_price"] == 500_000
    assert result["discount"] == 50_000
    assert result["net_price"] == 430_000
    assert result["stock_status"] == "IN_STOCK"


def test_invalid_upload_preserves_existing_catalog(db_session):
    db_session.add(
        models.Product(
            barcode="EXISTING",
            name="Existing Product",
            category="Skincare",
            guardian_price=100_000,
            cost_price=60_000,
        )
    )
    db_session.commit()

    invalid_csv = b"barcode,name,category,guardian_price\n,Missing Barcode,Skincare,0\n"
    with pytest.raises(ValueError, match="no valid product rows"):
        import_dataset_from_upload(db_session, "invalid.csv", invalid_csv)

    assert db_session.query(models.Product).count() == 1
    assert db_session.query(models.Product).first().barcode == "EXISTING"


def test_upload_reports_quality_and_parses_vietnamese_thousands(db_session):
    csv_payload = (
        "barcode,name,category,guardian_price,cost_price,shopee_url\n"
        "8930001,Cleanser,Skincare,136.000,82.000,https://shopee.vn/item-a\n"
        "8930001,Duplicate,Skincare,150.000,90.000,\n"
    ).encode("utf-8")

    result = import_dataset_from_upload(db_session, "catalog.csv", csv_payload)
    product = db_session.query(models.Product).one()

    assert result["received"] == 2
    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert result["data_quality_pct"] == 50.0
    assert result["validation_errors"][0]["errors"] == ["duplicate barcode in upload"]
    assert product.guardian_price == 136_000
    assert product.cost_price == 82_000
    assert db_session.query(models.CompetitorLink).count() == 1
