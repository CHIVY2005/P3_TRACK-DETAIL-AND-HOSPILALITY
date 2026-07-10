from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import case
from typing import List
from app.db.session import get_db
from app.db import models
from app import schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.Alert])
def list_alerts(
    unresolved_only: bool = True,
    severity: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Alert)
    if unresolved_only:
        query = query.filter(models.Alert.is_resolved == False)
    if severity:
        query = query.filter(models.Alert.severity == severity)
        
    severity_order = case(
        (models.Alert.severity == "High", 0),
        (models.Alert.severity == "Medium", 1),
        (models.Alert.severity == "Low", 2),
        else_=3,
    )
    return query.order_by(
        severity_order,
        models.Alert.created_at.desc()
    ).all()

@router.post("/{alert_id}/resolve", response_model=schemas.Alert)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found"
        )
    alert.is_resolved = True
    db.commit()
    db.refresh(alert)
    return alert
