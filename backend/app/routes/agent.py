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

def run_agent_in_background(db_session: Session):
    global is_agent_running
    is_agent_running = True
    try:
        run_agentic_optimization_loop(db_session)
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
            # Fetch the task record inside thread
            task_rec = thread_db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
            if task_rec:
                # Update status to Running
                task_rec.status = "Running"
                task_rec.logs = "[Agent Initialized] Starting autonomous competitive pricing sweep...\n"
                thread_db.commit()
                
                # Execute agent loop logic (inlined here or refactored to use existing task)
                from app.services.agent_engine import run_agentic_optimization_loop
                # Run the loop using the database session
                # Let's adjust agent_engine's run_agentic_optimization_loop to accept an existing task or run on it
                # To make it simple, we can run it and then copy details, or we can just run the function.
                # Let's clean it up: our run_agentic_optimization_loop creates its own task.
                # Let's delete the dummy task and let run_agentic_optimization_loop create and return a new one!
                # Wait, this is even simpler: we just delete the dummy task and run!
                thread_db.query(models.AgentTask).filter(models.AgentTask.id == task_id).delete()
                thread_db.commit()
                run_agentic_optimization_loop(thread_db)
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
