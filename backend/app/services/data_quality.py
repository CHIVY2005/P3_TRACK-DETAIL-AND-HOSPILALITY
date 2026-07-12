from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db import models
from app.services.channel_intelligence import MONITORED_CHANNELS, get_latest_channel_observations


def assess_product_data_quality(db: Session, product: models.Product) -> Dict[str, object]:
    """Score the evidence behind one product decision using observable signals only."""
    observations = get_latest_channel_observations(db, product_id=product.id)
    valid_observations = [
        row for row in observations if _is_valid_observation(row, product.guardian_price)
    ]
    now = datetime.now(timezone.utc)
    fresh_observations = [
        row for row in valid_observations
        if _age_hours(row.scraped_at, now) <= settings.PRICING_FRESHNESS_HOURS
    ]
    links = db.query(models.CompetitorLink).filter(
        models.CompetitorLink.product_id == product.id
    ).all()

    configured_channel_count = len(MONITORED_CHANNELS)
    observed_channels = {row.competitor_name for row in observations}
    valid_channels = {row.competitor_name for row in valid_observations}
    fresh_channels = {row.competitor_name for row in fresh_observations}
    linked_channels = {link.platform for link in links}

    coverage_pct = _percentage(len(observed_channels), configured_channel_count)
    validity_pct = _percentage(len(valid_observations), len(observations))
    freshness_pct = _percentage(len(fresh_channels), configured_channel_count)
    link_coverage_pct = _percentage(len(linked_channels), configured_channel_count)
    score_pct = round(
        (coverage_pct * 0.35)
        + (validity_pct * 0.30)
        + (freshness_pct * 0.25)
        + (link_coverage_pct * 0.10),
        2,
    )

    if score_pct >= 80:
        confidence_label = "High"
    elif score_pct >= 60:
        confidence_label = "Medium"
    else:
        confidence_label = "Low"

    missing_channels = sorted(set(MONITORED_CHANNELS).difference(observed_channels))
    reasons: List[str] = []
    if missing_channels:
        reasons.append(f"Missing observations: {', '.join(missing_channels)}")
    if len(valid_observations) < len(observations):
        reasons.append("Some observations are invalid, suspicious, or unavailable")
    if len(fresh_observations) < len(valid_observations):
        reasons.append(f"Some valid observations are older than {settings.PRICING_FRESHNESS_HOURS}h")
    if len(linked_channels) < configured_channel_count:
        reasons.append("Some channel links are not mapped yet")
    if not reasons:
        reasons.append("Multi-channel, fresh, valid evidence is available")

    return {
        "data_quality_pct": score_pct,
        "confidence_label": confidence_label,
        "data_quality_reasons": reasons,
        "observed_channels": len(observed_channels),
        "valid_channels": len(valid_channels),
        "fresh_channels": len(fresh_channels),
        "linked_channels": len(linked_channels),
        "coverage_pct": coverage_pct,
        "validity_pct": validity_pct,
        "freshness_pct": freshness_pct,
        "link_coverage_pct": link_coverage_pct,
        "latest_observation_at": max(
            (row.scraped_at for row in observations if row.scraped_at),
            default=None,
        ),
    }


def _is_valid_observation(row: models.CompetitorPrice, guardian_price: Optional[float]) -> bool:
    stock_status = (row.stock_status or "").replace("_", "").replace(" ", "").upper()
    return bool(
        guardian_price
        and guardian_price > 0
        and row.net_price
        and row.net_price > 0
        and not row.is_suspicious
        and stock_status not in {"OUTOFSTOCK", "OOS", "UNAVAILABLE"}
    )


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100.0, 2)


def _age_hours(value: Optional[datetime], now: datetime) -> float:
    if value is None:
        return float("inf")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max((now - value.astimezone(timezone.utc)).total_seconds() / 3600.0, 0.0)
