from collections import defaultdict
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.config import get_agent_config
from app.db import models
from app.agents.market_observer.market_observer_tools import (
    get_alert_reference_price,
    get_latest_channel_observations,
    is_clean_price,
    select_reference_price,
)


def build_alert_decision_context(db: Session, alert: models.Alert) -> Dict[str, Any]:
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "missing_product"}

    latest_price = get_alert_reference_price(db, product, alert.alert_type)
    if not latest_price:
        return {"status": "skipped", "reason": "missing_competitor_price"}

    return _build_context(alert, product, latest_price, get_agent_config())


def build_alert_decision_contexts(
    db: Session,
    alerts: List[models.Alert],
    products_by_id: Dict[int, models.Product] = None,
    observations: List[models.CompetitorPrice] = None,
) -> List[Dict[str, Any]]:
    """Batched equivalent of build_alert_decision_context that avoids N+1 queries.

    Instead of one product lookup + one windowed price query per alert, it preloads
    every product and the latest clean price for each product/channel pair once, then
    resolves each alert in memory. Turns ~2*len(alerts) round-trips into 3 queries.

    ``products_by_id`` and ``observations`` may be passed in when the caller already
    loaded them (e.g. the briefing route also feeds channel intelligence) so the two
    heavy queries run only once per request.
    """
    if not alerts:
        return []

    if products_by_id is None:
        products_by_id = {product.id: product for product in db.query(models.Product).all()}
    if observations is None:
        observations = get_latest_channel_observations(db)

    clean_prices_by_product: Dict[int, list] = defaultdict(list)
    for row in observations:
        if is_clean_price(row):
            clean_prices_by_product[row.product_id].append(row)

    cfg = get_agent_config()

    contexts = []
    for alert in alerts:
        product = products_by_id.get(alert.product_id)
        if not product:
            contexts.append({"status": "skipped", "reason": "missing_product"})
            continue
        latest_price = select_reference_price(
            clean_prices_by_product.get(product.id, []), product, alert.alert_type
        )
        if not latest_price:
            contexts.append({"status": "skipped", "reason": "missing_competitor_price"})
            continue
        contexts.append(_build_context(alert, product, latest_price, cfg))
    return contexts


def _build_context(alert, product, latest_price, cfg) -> Dict[str, Any]:
    min_margin_pct = cfg.get("min_margin", 0.15) * 100.0
    current_margin_pct = ((product.guardian_price - product.cost_price) / product.guardian_price) * 100 if product.guardian_price else 0.0
    margin_if_matched_pct = ((latest_price.net_price - product.cost_price) / latest_price.net_price) * 100 if latest_price.net_price else 0.0
    price_gap_pct = ((product.guardian_price - latest_price.net_price) / product.guardian_price) * 100 if product.guardian_price else 0.0

    is_guardian_value = latest_price.net_price > product.guardian_price
    if margin_if_matched_pct >= min_margin_pct:
        strategy = "match"
        recommended_action = "Approve market-aligned price"
        if is_guardian_value:
            rationale = (
                f"Guardian is {abs(price_gap_pct):.1f}% below the nearest clean market reference at "
                f"{latest_price.competitor_name}. Aligning upward keeps margin at {margin_if_matched_pct:.1f}% "
                f"above the floor of {min_margin_pct:.1f}%."
            )
        else:
            rationale = (
                f"{latest_price.competitor_name} is cheaper by {price_gap_pct:.1f}% and margin after matching "
                f"remains {margin_if_matched_pct:.1f}% above the floor of {min_margin_pct:.1f}%."
            )
    else:
        strategy = "negotiate"
        recommended_action = "Draft supplier protection request"
        rationale = (
            f"Matching {latest_price.competitor_name} would drop margin to {margin_if_matched_pct:.1f}%, "
            f"below the floor of {min_margin_pct:.1f}%, so the safer move is supplier negotiation."
        )

    return {
        "status": "ready",
        "alert_id": alert.id,
        "product_id": product.id,
        "product_name": product.name,
        "category": product.category,
        "guardian_price": round(product.guardian_price, 2),
        "cost_price": round(product.cost_price, 2),
        "current_margin_pct": round(current_margin_pct, 2),
        "competitor_name": latest_price.competitor_name,
        "competitor_price": round(latest_price.net_price, 2),
        "price_gap_pct": round(price_gap_pct, 2),
        "margin_if_matched_pct": round(margin_if_matched_pct, 2),
        "strategy": strategy,
        "recommended_action": recommended_action,
        "rationale": rationale,
        "severity": alert.severity,
        "message": alert.message,
        "channel_url": latest_price.url,
        "scraped_at": latest_price.scraped_at.isoformat() if latest_price.scraped_at else None,
        "data_quality_pct": quality["data_quality_pct"],
        "confidence_label": quality["confidence_label"],
        "data_quality_reasons": quality["data_quality_reasons"],
    }
