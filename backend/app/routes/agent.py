import json
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import schemas
from app.db import models
from app.db.session import get_db
from app.services.agent_engine import build_alert_decision_context, run_agentic_optimization_loop

router = APIRouter()

is_agent_running = False


class AgentRunRequest(BaseModel):
    refresh_market_data: bool = False


@router.post("/run", response_model=schemas.AgentTask, status_code=status.HTTP_202_ACCEPTED)
def trigger_agent_run(
    background_tasks: BackgroundTasks,
    payload: AgentRunRequest = AgentRunRequest(),
    db: Session = Depends(get_db),
):
    global is_agent_running
    if is_agent_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI Agent loop is already running in background.",
        )

    task = models.AgentTask(
        objective="Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index.",
        status="Pending",
        logs="[Agent Queued] Waiting to start autonomous watchtower run...",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    from app.db.session import SessionLocal

    def run_agent_thread(task_id: int):
        global is_agent_running
        is_agent_running = True
        thread_db = SessionLocal()
        try:
            run_agentic_optimization_loop(
                thread_db,
                task_id=task_id,
                refresh_market_data=payload.refresh_market_data,
            )
        except Exception as exc:
            print(f"Error in background agent task: {exc}")
        finally:
            is_agent_running = False
            thread_db.close()

    background_tasks.add_task(run_agent_thread, task.id)
    return task


@router.get("/briefing", response_model=schemas.AgentBriefing)
def get_agent_briefing(limit: int = 6, db: Session = Depends(get_db)):
    active_alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
    decisions = []
    for alert in active_alerts:
        context = build_alert_decision_context(db, alert)
        if context.get("status") == "ready":
            decisions.append(context)

    severity_rank = {"High": 0, "Medium": 1, "Low": 2}
    decisions.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 9),
            -abs(item["price_gap_pct"]),
            item["margin_if_matched_pct"],
        )
    )

    channel_rows = db.query(
        models.CompetitorPrice.competitor_name,
        func.avg(models.CompetitorPrice.net_price),
        func.count(func.distinct(models.CompetitorPrice.product_id)),
    ).filter(
        models.CompetitorPrice.net_price.isnot(None),
        models.CompetitorPrice.stock_status != "OUT_OF_STOCK",
        models.CompetitorPrice.is_suspicious == False,
    ).group_by(models.CompetitorPrice.competitor_name).all()

    channel_alert_counts = {
        row[0]: row[1]
        for row in db.query(
            models.CompetitorPrice.competitor_name,
            func.count(models.Alert.id),
        ).join(
            models.Alert,
            models.Alert.product_id == models.CompetitorPrice.product_id,
        ).filter(
            models.Alert.is_resolved == False,
            models.CompetitorPrice.net_price.isnot(None),
            models.CompetitorPrice.stock_status != "OUT_OF_STOCK",
            models.CompetitorPrice.is_suspicious == False,
        ).group_by(models.CompetitorPrice.competitor_name).all()
    }

    channel_summary = [
        schemas.AgentBriefingChannel(
            channel=channel,
            avg_net_price=round(avg_net_price or 0.0, 2),
            sku_coverage=sku_coverage,
            alert_count=channel_alert_counts.get(channel, 0),
        )
        for channel, avg_net_price, sku_coverage in channel_rows
    ]
    channel_summary.sort(key=lambda item: (-item.alert_count, item.channel))

    latest_task = db.query(models.AgentTask).order_by(models.AgentTask.started_at.desc()).first()
    pending_actions = db.query(models.AgentAction).filter(models.AgentAction.status == "Pending").count()
    monitored_sku = db.query(models.Product).count()
    average_cpi = db.query(func.avg(models.PricingIndex.competitor_index)).scalar() or 100.0
    high_alerts = sum(1 for alert in active_alerts if alert.severity == "High")
    last_scrape_at = db.query(func.max(models.CompetitorPrice.scraped_at)).scalar()

    return schemas.AgentBriefing(
        summary=schemas.AgentBriefingSummary(
            monitored_sku=monitored_sku,
            active_alerts=len(active_alerts),
            high_severity_alerts=high_alerts,
            pending_actions=pending_actions,
            average_cpi=round(average_cpi, 2),
            channels_covered=len(channel_summary),
            last_scrape_at=last_scrape_at,
        ),
        priority_queue=[schemas.AgentBriefingPriority(**item) for item in decisions[:limit]],
        channel_summary=channel_summary,
        latest_task=latest_task,
    )


@router.get("/tasks", response_model=List[schemas.AgentTask])
def list_agent_tasks(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.AgentTask).order_by(models.AgentTask.started_at.desc()).limit(limit).all()


@router.get("/tasks/{task_id}", response_model=schemas.AgentTask)
def get_agent_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent task with id {task_id} not found",
        )
    return task


@router.get("/actions", response_model=List[schemas.AgentAction])
def list_agent_actions(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.AgentAction).order_by(models.AgentAction.created_at.desc()).limit(limit).all()


@router.post("/actions/{action_id}/approve")
def approve_agent_action(action_id: int, db: Session = Depends(get_db)):
    action = db.query(models.AgentAction).filter(models.AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent action with id {action_id} not found",
        )
    if action.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action has already been {action.status.lower()}",
        )

    try:
        action.status = "Approved"

        if action.action_type == "AUTO_PRICE_MATCH":
            payload = json.loads(action.data)
            new_price = payload.get("new_price")
            product = db.query(models.Product).filter(models.Product.id == action.product_id).first()
            if product and new_price:
                product.guardian_price = float(new_price)

            unresolved_alerts = db.query(models.Alert).filter(
                models.Alert.product_id == action.product_id,
                models.Alert.is_resolved == False,
            ).all()
            for alert in unresolved_alerts:
                alert.is_resolved = True

        db.commit()
        return {"status": "success", "message": "Action approved and executed successfully."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing approval: {exc}",
        )


@router.post("/actions/{action_id}/reject")
def reject_agent_action(action_id: int, db: Session = Depends(get_db)):
    action = db.query(models.AgentAction).filter(models.AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent action with id {action_id} not found",
        )
    if action.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action has already been {action.status.lower()}",
        )

    try:
        action.status = "Rejected"
        unresolved_alerts = db.query(models.Alert).filter(
            models.Alert.product_id == action.product_id,
            models.Alert.is_resolved == False,
        ).all()
        for alert in unresolved_alerts:
            alert.is_resolved = True

        db.commit()
        return {"status": "success", "message": "Action rejected and alert dismissed."}
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing rejection: {exc}",
        )


@router.get("/config", response_model=schemas.AgentConfig)
def get_config():
    from app.config import get_agent_config

    return get_agent_config()


@router.post("/config")
def save_config(config: schemas.AgentConfig):
    from app.config import save_agent_config

    save_agent_config(config.model_dump())
    return {"status": "success", "message": "Configuration saved successfully."}
