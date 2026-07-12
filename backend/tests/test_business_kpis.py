from datetime import datetime, timezone

from app.db import models
from app.services.business_kpis import build_business_kpis
from app.services.data_quality import assess_product_data_quality
from app.services.channel_intelligence import MONITORED_CHANNELS


def _seed_quality_fixture(db_session):
    product = models.Product(
        barcode="KPI-1",
        name="KPI Test Product",
        category="Skincare",
        guardian_price=100_000,
        cost_price=60_000,
    )
    db_session.add(product)
    db_session.flush()
    now = datetime.now(timezone.utc)

    for channel in MONITORED_CHANNELS:
        db_session.add(
            models.CompetitorPrice(
                product_id=product.id,
                competitor_name=channel,
                raw_price=90_000,
                net_price=90_000,
                scraped_at=now,
            )
        )
        db_session.add(
            models.CompetitorLink(
                product_id=product.id,
                platform=channel,
                url=f"https://example.com/{channel.lower().replace(' ', '-')}",
                discovery_method="test",
            )
        )

    db_session.add(
        models.Alert(
            product_id=product.id,
            alert_type="Competitor Undercutting",
            message="Test pricing gap",
            severity="High",
            is_resolved=False,
        )
    )
    db_session.commit()
    return product


def test_product_quality_score_uses_fresh_valid_and_linked_evidence(db_session):
    product = _seed_quality_fixture(db_session)

    quality = assess_product_data_quality(db_session, product)

    assert quality["data_quality_pct"] == 100.0
    assert quality["confidence_label"] == "High"
    assert quality["observed_channels"] == len(MONITORED_CHANNELS)
    assert quality["data_quality_reasons"] == ["Multi-channel, fresh, valid evidence is available"]


def test_business_kpis_expose_decision_value_and_coverage(db_session):
    _seed_quality_fixture(db_session)

    kpis = build_business_kpis(db_session)

    assert kpis["monitored_sku"] == 1
    assert kpis["active_alerts"] == 1
    assert kpis["actionable_decisions"] == 1
    assert kpis["decision_coverage_pct"] == 100.0
    assert kpis["average_decision_confidence_pct"] == 100.0
    assert kpis["estimated_margin_exposure_vnd"] == 10_000.0
    assert kpis["pending_actions"] == 0
