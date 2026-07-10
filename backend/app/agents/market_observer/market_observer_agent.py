from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config import get_agent_config
from app.db import models
from app.agents.market_observer.market_observer_tools import get_alert_reference_price


def build_alert_decision_context(db: Session, alert: models.Alert) -> Dict[str, Any]:
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "missing_product"}

    latest_price = get_alert_reference_price(db, product, alert.alert_type)
    if not latest_price:
        return {"status": "skipped", "reason": "missing_competitor_price"}

    cfg = get_agent_config()
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
    }
