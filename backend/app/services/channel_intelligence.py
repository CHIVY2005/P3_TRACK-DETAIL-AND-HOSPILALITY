from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_agent_config, settings
from app.db import models


MONITORED_CHANNELS = (
    "Shopee",
    "Lazada",
    "TikTok Shop",
    "GrabMart",
    "Pharmacity",
    "Hasaki",
)


def get_latest_channel_observations(
    db: Session,
    product_id: Optional[int] = None,
) -> List[models.CompetitorPrice]:
    """Return one deterministic latest row for every product/channel pair."""
    ranked_query = db.query(
        models.CompetitorPrice.id.label("price_id"),
        func.row_number()
        .over(
            partition_by=(
                models.CompetitorPrice.product_id,
                models.CompetitorPrice.competitor_name,
            ),
            order_by=(
                models.CompetitorPrice.scraped_at.desc(),
                models.CompetitorPrice.id.desc(),
            ),
        )
        .label("observation_rank"),
    )
    if product_id is not None:
        ranked_query = ranked_query.filter(models.CompetitorPrice.product_id == product_id)
    ranked = ranked_query.subquery()

    return (
        db.query(models.CompetitorPrice)
        .join(ranked, models.CompetitorPrice.id == ranked.c.price_id)
        .filter(ranked.c.observation_rank == 1)
        .all()
    )


def build_channel_intelligence(db: Session) -> Dict[str, object]:
    products = db.query(models.Product).all()
    guardian_prices = {product.id: product.guardian_price for product in products}
    observations = get_latest_channel_observations(db)

    observed_channels = {row.competitor_name for row in observations}
    channels = list(MONITORED_CHANNELS)
    channels.extend(sorted(observed_channels.difference(MONITORED_CHANNELS)))

    now = datetime.now(timezone.utc)
    freshness_hours = settings.PRICING_FRESHNESS_HOURS
    agent_config = get_agent_config()
    overprice_limit = 100.0 * (1.0 + agent_config.get("overprice_threshold", 0.10))
    underprice_limit = 100.0 * (1.0 - agent_config.get("underprice_threshold", 0.10))
    total_sku = len(products)
    expected_observations = total_sku * len(channels)

    channel_rows = []
    all_valid_rows = []
    all_fresh_rows = []
    all_price_relatives = []
    promotion_observations = 0
    pricing_opportunities = 0

    for channel in channels:
        rows = [row for row in observations if row.competitor_name == channel]
        valid_rows = [row for row in rows if _is_comparable(row, guardian_prices.get(row.product_id))]
        fresh_rows = [row for row in valid_rows if _age_hours(row.scraped_at, now) <= freshness_hours]
        price_relatives = [
            guardian_prices[row.product_id] / row.net_price * 100.0
            for row in valid_rows
        ]
        promo_rows = [row for row in valid_rows if _has_promotion(row)]
        voucher_rows = [row for row in valid_rows if bool((row.voucher_details or "").strip())]
        bundle_rows = [row for row in valid_rows if _contains_any(row.promo_mechanics, ("bundle", "combo", "buy 2", "mua 2"))]
        flash_rows = [row for row in valid_rows if _contains_any(row.promo_mechanics, ("flash", "livestream"))]
        premium_sku = sum(1 for value in price_relatives if value > overprice_limit)
        value_sku = sum(1 for value in price_relatives if value < underprice_limit)
        channel_opportunities = premium_sku + value_sku
        cpi = _average(price_relatives, 100.0)

        all_valid_rows.extend(valid_rows)
        all_fresh_rows.extend(fresh_rows)
        all_price_relatives.extend(price_relatives)
        promotion_observations += len(promo_rows)
        pricing_opportunities += channel_opportunities

        latest_at = max((row.scraped_at for row in rows if row.scraped_at), default=None)
        channel_rows.append(
            {
                "channel": channel,
                "cpi": round(cpi, 2),
                "price_gap_pct": round(cpi - 100.0, 2),
                "position": _market_position(cpi, overprice_limit, underprice_limit),
                "avg_guardian_price": round(
                    _average((guardian_prices[row.product_id] for row in valid_rows), 0.0),
                    2,
                ),
                "avg_net_price": round(_average((row.net_price for row in valid_rows), 0.0), 2),
                "sku_coverage": len(valid_rows),
                "coverage_pct": _percentage(len(valid_rows), total_sku),
                "observation_coverage_pct": _percentage(len(rows), total_sku),
                "freshness_pct": _percentage(len(fresh_rows), total_sku),
                "data_quality_pct": _percentage(len(valid_rows), len(rows)),
                "promotion_sku": len(promo_rows),
                "promotion_coverage_pct": _percentage(len(promo_rows), len(valid_rows)),
                "voucher_sku": len(voucher_rows),
                "bundle_sku": len(bundle_rows),
                "flash_sale_sku": len(flash_rows),
                "guardian_premium_sku": premium_sku,
                "guardian_value_sku": value_sku,
                "opportunity_count": channel_opportunities,
                "latest_scrape_at": latest_at,
            }
        )

    latest_observation_at = max(
        (row.scraped_at for row in observations if row.scraped_at),
        default=None,
    )
    observed_sku = len({row.product_id for row in observations})
    fresh_sku = len({row.product_id for row in all_fresh_rows})

    return {
        "summary": {
            "target_sku": settings.PRICING_TARGET_SKU_COUNT,
            "monitored_sku": total_sku,
            "target_coverage_pct": min(
                _percentage(total_sku, settings.PRICING_TARGET_SKU_COUNT),
                100.0,
            ),
            "observed_sku": observed_sku,
            "fresh_sku": fresh_sku,
            "configured_channels": len(channels),
            "channels_with_data": sum(1 for row in channel_rows if row["observation_coverage_pct"] > 0),
            "overall_cpi": round(_average(all_price_relatives, 100.0), 2),
            "automated_observation_coverage_pct": _percentage(len(observations), expected_observations),
            "valid_observation_pct": _percentage(len(all_valid_rows), len(observations)),
            "fresh_observation_pct": _percentage(len(all_fresh_rows), expected_observations),
            "freshness_sla_hours": freshness_hours,
            "promotion_observations": promotion_observations,
            "pricing_opportunities": pricing_opportunities,
            "latest_observation_at": latest_observation_at,
            "latest_observation_age_hours": (
                round(_age_hours(latest_observation_at, now), 2)
                if latest_observation_at
                else None
            ),
        },
        "channels": channel_rows,
    }


def _is_comparable(row: models.CompetitorPrice, guardian_price: Optional[float]) -> bool:
    stock_status = (row.stock_status or "").replace("_", "").replace(" ", "").upper()
    return bool(
        guardian_price
        and guardian_price > 0
        and row.net_price
        and row.net_price > 0
        and not row.is_suspicious
        and stock_status not in {"OUTOFSTOCK", "OOS", "UNAVAILABLE"}
    )


def _has_promotion(row: models.CompetitorPrice) -> bool:
    return bool(
        (row.discount or 0.0) > 0
        or (row.voucher_details or "").strip()
        or (row.promo_mechanics or "").strip()
    )


def _contains_any(value: Optional[str], terms: Iterable[str]) -> bool:
    normalized = (value or "").lower()
    return any(term in normalized for term in terms)


def _average(values: Iterable[float], default: float) -> float:
    materialized = [float(value) for value in values if value is not None]
    return sum(materialized) / len(materialized) if materialized else default


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100.0, 2)


def _age_hours(value: datetime, now: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max((now - value.astimezone(timezone.utc)).total_seconds() / 3600.0, 0.0)


def _market_position(cpi: float, overprice_limit: float, underprice_limit: float) -> str:
    if cpi > overprice_limit:
        return "guardian_premium"
    if cpi < underprice_limit:
        return "guardian_value"
    return "parity"
