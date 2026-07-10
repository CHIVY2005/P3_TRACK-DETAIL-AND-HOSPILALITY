from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.agents.market_observer.market_observer_agent import build_alert_decision_context
from app.agents.market_observer.market_observer_tools import refresh_market_prices
from app.agents.margin_guardian.margin_guardian_agent import run_margin_guardian_for_alert
from app.agents.shared.runtime_support import get_langfuse_client


def run_agentic_optimization_loop(
    db: Session,
    task_id: Optional[int] = None,
    refresh_market_data: bool = True,
    max_alerts: int = 6,
) -> models.AgentTask:
    task = None
    if task_id is not None:
        task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()

    if not task:
        task = models.AgentTask(
            objective="Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index.",
            status="Running",
            logs="[Agent Initialized] Starting autonomous pricing watchtower...\n",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
    else:
        task.objective = "Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index."
        task.status = "Running"
        task.logs = "[Agent Initialized] Starting autonomous pricing watchtower...\n"
        task.completed_at = None
        db.commit()
        db.refresh(task)

    logs = [f"[Agent Task ID {task.id}] Objective: {task.objective}"]
    langfuse = get_langfuse_client()

    def _run_loop():
        if refresh_market_data:
            logs.append("[Perceive] Refreshing competitor prices across tracked channels...")
            task.logs = "\n".join(logs)
            db.commit()
            scrape_results = refresh_market_prices(db)
            item_count = sum(len(result or []) for result in scrape_results.values())
            logs.append(
                f"[Perceive Complete] Scraper refreshed {len(scrape_results)} products and recorded {item_count} channel observations."
            )
            task.logs = "\n".join(logs)
            db.commit()
        else:
            logs.append("[Perceive] Skipped live refresh. Using latest stored competitor data.")
            task.logs = "\n".join(logs)
            db.commit()

        alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
        selected_alerts = _select_priority_alerts(db, alerts, max_alerts)
        logs.append(
            f"[Reason] Detected {len(alerts)} unresolved alerts and selected "
            f"{len(selected_alerts)} unique SKU decisions after ranking."
        )
        task.logs = "\n".join(logs)
        db.commit()

        if not selected_alerts:
            logs.append("No active alerts. System remains stable.")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            task.logs = "\n".join(logs)
            db.commit()
            return task

        for alert in selected_alerts:
            agent_result = run_margin_guardian_for_alert(db, alert)
            for agent_log in agent_result.get("logs", []):
                logs.append(f"  {agent_log}")

            for act in agent_result.get("actions_created", []):
                pending_action = db.query(models.AgentAction).filter(
                    models.AgentAction.product_id == alert.product_id,
                    models.AgentAction.action_type == act["action_type"],
                    models.AgentAction.status == "Pending",
                ).first()
                if pending_action:
                    logs.append(
                        f"  [Guardrail] Reused pending action #{pending_action.id}; "
                        "no duplicate approval request created."
                    )
                    continue

                action_record = models.AgentAction(
                    task_id=task.id,
                    product_id=alert.product_id,
                    action_type=act["action_type"],
                    description=act["description"],
                    status="Pending",
                    data=act["data"],
                )
                db.add(action_record)

            db.commit()
            task.logs = "\n".join(logs)
            db.commit()

        task.status = "Completed"
        logs.append("[Act Complete] All selected alerts were processed through the pricing workflow.")
        task.completed_at = datetime.utcnow()
        task.logs = "\n".join(logs)
        db.commit()
        return task

    try:
        if langfuse:
            with langfuse.start_as_current_observation(
                as_type="span",
                name="pricing-agent-run",
                input={"task_id": task.id, "objective": task.objective},
            ) as root_span:
                result = _run_loop()
                root_span.update(
                    output={
                        "status": result.status,
                        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    }
                )
                return result

        return _run_loop()
    except Exception as exc:
        logs.append(f"[CRITICAL ERROR] {exc}")
        task.status = "Failed"
        task.completed_at = datetime.utcnow()
        task.logs = "\n".join(logs)
        db.commit()
        return task


def _select_priority_alerts(db: Session, alerts: list, limit: int) -> list:
    ranked = []
    for alert in alerts:
        context = build_alert_decision_context(db, alert)
        if context.get("status") != "ready":
            continue
        severity = {"High": 0, "Medium": 1, "Low": 2}.get(context.get("severity"), 9)
        ranked.append(
            (
                severity,
                -abs(context.get("price_gap_pct", 0.0)),
                context.get("margin_if_matched_pct", 0.0),
                alert.id,
                alert,
            )
        )

    selected = []
    seen_products = set()
    for *_, alert in sorted(ranked):
        if alert.product_id in seen_products:
            continue
        selected.append(alert)
        seen_products.add(alert.product_id)
        if len(selected) >= limit:
            break
    return selected
