from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db import models
from app import schemas
from app.services.agent_engine import run_agentic_optimization_loop

router = APIRouter()

# In-memory status flag to prevent parallel agent runs
is_agent_running = False

def run_agent_in_background(db_session: Session, task_id: int):
    global is_agent_running
    is_agent_running = True
    try:
        run_agentic_optimization_loop(db_session, task_id)
    except Exception as e:
        print(f"Background agent execution failed: {e}")
    finally:
        is_agent_running = False
        db_session.close()

@router.post("/run", response_model=schemas.AgentTask, status_code=status.HTTP_202_ACCEPTED)
def trigger_agent_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    global is_agent_running
    if is_agent_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI Agent loop is already running in background."
        )
    
    # Create an initial Pending task to return to client immediately
    task = models.AgentTask(
        objective="Analyze active price discrepancies, protect profit margins, and optimize competitor index.",
        status="Pending",
        logs="[Agent Queued] Waiting to start..."
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Spawn background thread with its own db session
    from app.db.session import SessionLocal
    bg_db = SessionLocal()
    
    # We delete the dummy task we just created inside the thread or update it.
    # To keep it clean, let's pass the task.id so the agent thread loads and updates this exact task!
    def run_agent_thread(task_id: int):
        global is_agent_running
        is_agent_running = True
        thread_db = SessionLocal()
        try:
            from app.services.agent_engine import run_agentic_optimization_loop
            run_agentic_optimization_loop(thread_db, task_id)
        except Exception as e:
            print(f"Error in background agent task: {e}")
        finally:
            is_agent_running = False
            thread_db.close()

    background_tasks.add_task(run_agent_thread, task.id)
    
    return task

@router.get("/tasks", response_model=List[schemas.AgentTask])
def list_agent_tasks(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.AgentTask).order_by(models.AgentTask.started_at.desc()).limit(limit).all()

@router.get("/tasks/{task_id}", response_model=schemas.AgentTask)
def get_agent_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent task with id {task_id} not found"
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
            detail=f"Agent action with id {action_id} not found"
        )
        
    if action.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action has already been {action.status.lower()}"
        )
        
    try:
        # Update action status
        action.status = "Approved"
        
        # If it is a price match, apply the price to the product
        if action.action_type == "AUTO_PRICE_MATCH":
            import json
            payload = json.loads(action.data)
            new_price = payload.get("new_price")
            
            product = db.query(models.Product).filter(models.Product.id == action.product_id).first()
            if product and new_price:
                product.guardian_price = float(new_price)
                
            # Resolve related unresolved alerts for this product
            unresolved_alerts = db.query(models.Alert).filter(
                models.Alert.product_id == action.product_id,
                models.Alert.is_resolved == False
            ).all()
            for alert in unresolved_alerts:
                alert.is_resolved = True
                
        db.commit()
        return {"status": "success", "message": f"Action approved and executed successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing approval: {str(e)}"
        )

@router.post("/actions/{action_id}/reject")
def reject_agent_action(action_id: int, db: Session = Depends(get_db)):
    action = db.query(models.AgentAction).filter(models.AgentAction.id == action_id).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent action with id {action_id} not found"
        )
        
    if action.status != "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action has already been {action.status.lower()}"
        )
        
    try:
        action.status = "Rejected"
        
        # Resolve related unresolved alerts since the user decided not to act on them
        unresolved_alerts = db.query(models.Alert).filter(
            models.Alert.product_id == action.product_id,
            models.Alert.is_resolved == False
        ).all()
        for alert in unresolved_alerts:
            alert.is_resolved = True
            
        db.commit()
        return {"status": "success", "message": f"Action rejected and alert dismissed."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing rejection: {str(e)}"
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
