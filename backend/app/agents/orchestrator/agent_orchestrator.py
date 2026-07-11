from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.agents.market_observer.market_observer_agent import build_alert_decision_context, run_market_observer_cycle
from app.agents.margin_guardian.margin_guardian_agent import run_margin_guardian_for_alert
from app.agents.shared.runtime_support import get_langfuse_client, set_active_agent, update_live_runtime


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
        set_active_agent("orchestrator", phase="planning", thought="Opening the daily pricing command cycle.")
        logs.append("[Perceive] Market Observer is collecting or loading competitor signals...")
        task.logs = "\n".join(logs)
        db.commit()
        market_result = run_market_observer_cycle(db, refresh_market_data=refresh_market_data)
        for observer_log in market_result.get("logs", []):
            logs.append(f"  {observer_log}")
        summary = market_result.get("summary", {})
        if refresh_market_data:
            logs.append(
                f"[Perceive Complete] Scraper refreshed {summary.get('products_refreshed', 0)} products and "
                f"recorded {summary.get('observations_recorded', 0)} channel observations via {summary.get('source', 'configured connectors')}."
            )
        else:
            logs.append(
                f"[Perceive Complete] Reused {summary.get('signals_ready', 0)} stored market signal sets "
                "without a live scrape."
            )
        task.logs = "\n".join(logs)
        db.commit()

        set_active_agent("market_observer", phase="sensemaking", thought="Ranking unresolved alerts and selecting the most important SKU decisions.")
        alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
        selected_alerts = _select_priority_alerts(db, alerts, max_alerts)
        logs.append(
            f"[Reason] Detected {len(alerts)} unresolved alerts and selected "
            f"{len(selected_alerts)} unique SKU decisions after ranking."
        )
        task.logs = "\n".join(logs)
        db.commit()

        if not selected_alerts:
            set_active_agent("orchestrator", phase="completed", thought="No active alerts were found, so no action is required.")
            logs.append("No active alerts. System remains stable.")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            task.logs = "\n".join(logs)
            db.commit()
            return task

        for alert in selected_alerts:
            set_active_agent(
                "margin_guardian",
                phase="reasoning",
                thought=f"Reviewing alert #{alert.id} and deciding whether Guardian should match price or protect margin.",
            )
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
            update_live_runtime(
                active_agent=agent_result.get("active_agent", "margin_guardian"),
                phase="action_queued",
                current_tool=None,
                tool_status="success",
                current_thought=agent_result.get("decision_reason") or "Action proposal has been recorded for approval.",
            )

        task.status = "Completed"
        set_active_agent("orchestrator", phase="completed", thought="All selected alerts have been processed and queued for commercial review.")
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
