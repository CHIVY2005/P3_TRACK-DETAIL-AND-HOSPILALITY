from datetime import datetime, timedelta, timezone

from app.agents.market_observer.market_observer_tools import get_alert_reference_price
from app.db import models


def test_agent_uses_clean_latest_market_reference(db_session):
    product = models.Product(
        barcode="AGENT-1",
        name="Agent Test Product",
        category="Skincare",
        guardian_price=100_000,
        cost_price=60_000,
    )
    db_session.add(product)
    db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            models.CompetitorPrice(
                product_id=product.id,
                competitor_name="Shopee",
                net_price=70_000,
                scraped_at=now - timedelta(days=1),
            ),
            models.CompetitorPrice(
                product_id=product.id,
                competitor_name="Shopee",
                net_price=80_000,
                scraped_at=now,
            ),
            models.CompetitorPrice(
                product_id=product.id,
                competitor_name="GrabMart",
                net_price=120_000,
                scraped_at=now,
            ),
            models.CompetitorPrice(
                product_id=product.id,
                competitor_name="TikTok Shop",
                net_price=50_000,
                is_suspicious=True,
                scraped_at=now,
            ),
        ]
    )
    db_session.commit()

    undercut_reference = get_alert_reference_price(db_session, product, "Competitor Undercutting")
    value_reference = get_alert_reference_price(db_session, product, "Underpriced")

    assert undercut_reference.competitor_name == "Shopee"
    assert undercut_reference.net_price == 80_000
    assert value_reference.competitor_name == "GrabMart"
    assert value_reference.net_price == 120_000
