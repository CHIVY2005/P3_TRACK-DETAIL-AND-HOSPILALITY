from datetime import datetime, timezone

from app.db import models
from app.services.demo_seed import seed_demo_dataset


def test_demo_seed_proves_top_200_sku_and_six_channel_history(db_session):
    result = seed_demo_dataset(db_session)

    assert result["products"] == 200
    assert result["competitor_prices"] == 8400
    assert result["competitor_links"] == 1200
    assert db_session.query(models.Product).count() == 200
    assert db_session.query(models.CompetitorLink).count() == 1200

    channels = {
        name
        for (name,) in db_session.query(models.CompetitorPrice.competitor_name).distinct().all()
    }
    assert channels == {"Shopee", "Lazada", "TikTok Shop", "GrabMart", "Pharmacity", "Hasaki"}

    latest = db_session.query(models.CompetitorPrice.scraped_at).order_by(
        models.CompetitorPrice.scraped_at.desc()
    ).first()[0]
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    assert (datetime.now(timezone.utc) - latest).total_seconds() < 30
