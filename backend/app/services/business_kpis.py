from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models
from app.services.channel_intelligence import build_channel_intelligence
from app.services.data_quality import assess_product_data_quality


def build_business_kpis(db: Session) -> Dict[str, object]:
    """Build a judge-friendly scorecard from persisted pricing and agent outcomes."""
    from app.agents.market_observer.market_observer_agent import build_alert_decision_context

    products = db.query(models.Product).all()
    active_alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
    decisions_by_product = {}
    for alert in active_alerts:
        context = build_alert_decision_context(db, alert)
        if context.get("status") != "ready":
            continue
        existing = decisions_by_product.get(context["product_id"])
        if existing is None or _decision_sort_key(context) < _decision_sort_key(existing):
            decisions_by_product[context["product_id"]] = context

    decisions = list(decisions_by_product.values())
    quality_scores = [
        assess_product_data_quality(db, product)["data_quality_pct"]
        for product in products
    ]
    high_confidence_decisions = sum(
        1 for decision in decisions if decision.get("confidence_label") == "High"
    )
    margin_exposure_vnd = sum(
        max(decision["guardian_price"] - decision["competitor_price"], 0.0)
        for decision in decisions
    )
    protected_exposure_vnd = sum(
        max(decision["guardian_price"] - decision["competitor_price"], 0.0)
        for decision in decisions
        if decision.get("strategy") == "negotiate"
    )
    alignment_opportunity_vnd = sum(
        max(decision["competitor_price"] - decision["guardian_price"], 0.0)
        for decision in decisions
        if decision.get("strategy") == "match"
    )

    actions = db.query(models.AgentAction).all()
    approved_actions = sum(1 for action in actions if action.status in {"Approved", "Executed"})
    rejected_actions = sum(1 for action in actions if action.status == "Rejected")
    reviewed_actions = approved_actions + rejected_actions
    completed_tasks = db.query(models.AgentTask).filter(models.AgentTask.status == "Completed").all()
    latest_task = db.query(models.AgentTask).order_by(models.AgentTask.started_at.desc()).first()

    channel_summary = build_channel_intelligence(db)["summary"]
    monitored_sku = len(products)
    quality_average = _average(quality_scores, 0.0)
    active_alert_count = len(active_alerts)
    decision_coverage_pct = _percentage(len(decisions), active_alert_count)

    return {
        "monitored_sku": monitored_sku,
        "active_alerts": active_alert_count,
        "actionable_decisions": len(decisions),
        "decision_coverage_pct": decision_coverage_pct,
        "average_data_quality_pct": round(quality_average, 2),
        "average_decision_confidence_pct": round(
            _average([decision.get("data_quality_pct", 0.0) for decision in decisions], quality_average),
            2,
        ),
        "high_confidence_decisions": high_confidence_decisions,
        "fresh_observation_pct": channel_summary["fresh_observation_pct"],
        "valid_observation_pct": channel_summary["valid_observation_pct"],
        "automated_coverage_pct": channel_summary["automated_observation_coverage_pct"],
        "estimated_margin_exposure_vnd": round(margin_exposure_vnd, 2),
        "estimated_protected_exposure_vnd": round(protected_exposure_vnd, 2),
        "alignment_opportunity_vnd": round(alignment_opportunity_vnd, 2),
        "pending_actions": sum(1 for action in actions if action.status == "Pending"),
        "approved_actions": approved_actions,
        "rejected_actions": rejected_actions,
        "recommendation_acceptance_pct": round(_percentage(approved_actions, reviewed_actions), 2),
        "completed_cycles": len(completed_tasks),
        "latest_cycle_duration_seconds": _duration_seconds(latest_task),
        "latest_cycle_status": latest_task.status if latest_task else "Idle",
        "latest_cycle_completed_at": latest_task.completed_at if latest_task else None,
    }


def _decision_sort_key(item: Dict[str, object]):
    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    return (
        severity_rank.get(item.get("severity"), 9),
        -abs(item.get("price_gap_pct", 0.0)),
        item.get("margin_if_matched_pct", 0.0),
    )


def _average(values, default: float) -> float:
    materialized = [float(value) for value in values if value is not None]
    return sum(materialized) / len(materialized) if materialized else default


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 100.0 if numerator == 0 else 0.0
    return round(numerator / denominator * 100.0, 2)


def _duration_seconds(task: models.AgentTask) -> float:
    if not task or not task.started_at or not task.completed_at:
        return 0.0
    started = task.started_at
    completed = task.completed_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    if completed.tzinfo is None:
        completed = completed.replace(tzinfo=timezone.utc)
    return round(max((completed - started).total_seconds(), 0.0), 2)
