from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.db import models
from app.scraper.scraper_engine import run_scraper_for_all_products, scrape_realtime_competitor_prices
from app import schemas
from app.services.scraped_samples import load_branch_scrape_samples

router = APIRouter()

class ScrapeTriggerRequest(BaseModel):
    product_id: Optional[int] = None

# In-memory status for simplified hackathon boilerplate
scraper_status = {
    "is_running": False,
    "last_run_completed": None,
    "items_scraped": 0
}

def bg_scrape_task(db_session: Session, product_id: Optional[int] = None):
    global scraper_status
    scraper_status["is_running"] = True
    try:
        if product_id:
            scrape_realtime_competitor_prices(db_session, product_id)
            scraper_status["items_scraped"] = 5  # 5 competitors
        else:
            results = run_scraper_for_all_products(db_session)
            scraper_status["items_scraped"] = len(results) * 5
        
        from datetime import datetime
        scraper_status["last_run_completed"] = datetime.utcnow().isoformat()
    except Exception as e:
        print(f"Scraper error: {e}")
    finally:
        scraper_status["is_running"] = False
        db_session.close()

@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
def trigger_scrape(
    payload: ScrapeTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    global scraper_status
    if scraper_status["is_running"]:
        return {"status": "already_running", "message": "Scrape task is currently running."}

    # We pass a new DB session for background tasks to avoid session sharing issues
    from app.db.session import SessionLocal
    bg_db = SessionLocal()
    
    background_tasks.add_task(bg_scrape_task, bg_db, payload.product_id)
    
    return {
        "status": "triggered",
        "message": "Scraping pipeline triggered in background.",
        "product_id": payload.product_id
    }

@router.get("/status")
def get_scraper_status():
    global scraper_status
    return scraper_status


@router.get("/branch-samples", response_model=list[schemas.ScrapeSample])
def get_branch_samples(db: Session = Depends(get_db)):
    return load_branch_scrape_samples(db)
