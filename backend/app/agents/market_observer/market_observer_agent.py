import os
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.config import get_agent_config
from app.db import models
from app.agents.market_observer.market_observer_tools import get_alert_reference_price, refresh_market_prices
from app.agents.shared.runtime_support import append_log, run_agent_tool, set_active_agent, update_live_runtime
from app.services.data_quality import assess_product_data_quality


def run_market_observer_cycle(db: Session, refresh_market_data: bool = True) -> Dict[str, Any]:
    """Run the market-observation stage with an auditable live progress stream."""
    products = db.query(models.Product).all()
    state: Dict[str, Any] = {"logs": [], "tool_events": []}
    results: Dict[int, list] = {}
    source = "live connectors" if os.getenv("ENABLE_REAL_SCRAPING") == "True" else "deterministic fixture fallback"

    if not refresh_market_data:
        set_active_agent(
            "market_observer",
            phase="perceive",
            thought="Loading the latest stored market signals because live refresh is disabled for this run.",
        )
        summary = run_agent_tool(
            state,
            "load_latest_market_signals",
            {"product_count": len(products)},
            lambda: {
                "products_available": len(products),
                "signals_ready": sum(1 for product in products if product.competitor_prices),
                "source": "stored observations",
            },
        )
        append_log(state, "[Market Observer] Reused the latest stored competitor observations.")
        return {"summary": summary, "results": results, "logs": state["logs"], "tool_events": state["tool_events"]}

    set_active_agent(
        "market_observer",
        phase="perceive",
        thought=f"Scanning {len(products)} catalog products across competitor channels using {source}.",
    )

    def on_progress(product: models.Product, index: int, total: int, status: str) -> None:
        product_name = product.name or f"Product #{product.id}"
        if status == "started":
            thought = f"Observing {product_name}: discovering links and collecting the latest channel prices."
        else:
            thought = f"Observed {product_name}: normalized channel prices and stored the market snapshot."
        set_active_agent("market_observer", phase="perceive", thought=thought)
        update_live_runtime(
            current_product={"id": product.id, "name": product_name},
            progress={"completed": index if status == "completed" else max(index - 1, 0), "total": total},
        )

    def refresh() -> Dict[str, Any]:
        nonlocal results
        results = refresh_market_prices(db, progress_callback=on_progress)
        observations = sum(len(result or []) for result in results.values())
        return {
            "products_refreshed": len(results),
            "observations_recorded": observations,
            "source": source,
        }

    summary = run_agent_tool(
        state,
        "refresh_competitor_market",
        {"product_count": len(products), "channels": "Shopee, Lazada, TikTok Shop, GrabMart, Pharmacity, Hasaki"},
        refresh,
    )
    update_live_runtime(current_product=None, progress={"completed": len(products), "total": len(products)})
    set_active_agent(
        "market_observer",
        phase="sensemaking",
        thought="Market observations are normalized. Ranking unresolved alerts by severity, gap, and margin risk.",
    )
    append_log(state, f"[Market Observer] Captured {summary['observations_recorded']} observations from {summary['products_refreshed']} products.")
    return {"summary": summary, "results": results, "logs": state["logs"], "tool_events": state["tool_events"]}


def build_alert_decision_context(db: Session, alert: models.Alert) -> Dict[str, Any]:
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "missing_product"}

    latest_price = get_alert_reference_price(db, product, alert.alert_type)
    if not latest_price:
        return {"status": "skipped", "reason": "missing_competitor_price"}

    cfg = get_agent_config()
    quality = assess_product_data_quality(db, product)
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
