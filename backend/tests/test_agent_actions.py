import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import get_db
from app.routes import agent
from app.services.cpi_calculator import calculate_cpi_for_product


def test_approved_price_action_recalculates_cpi(db_session, monkeypatch):
    product = models.Product(
        barcode="APPROVE-1",
        name="Approval Product",
        category="Skincare",
        guardian_price=100_000,
        cost_price=50_000,
    )
    task = models.AgentTask(objective="test", status="Completed")
    db_session.add_all([product, task])
    db_session.flush()
    db_session.add(
        models.CompetitorPrice(
            product_id=product.id,
            competitor_name="Shopee",
            raw_price=80_000,
            net_price=80_000,
        )
    )
    db_session.flush()
    calculate_cpi_for_product(db_session, product.id)

    action = models.AgentAction(
        task_id=task.id,
        product_id=product.id,
        action_type="AUTO_PRICE_MATCH",
        description="Align price",
        status="Pending",
        data=json.dumps({"new_price": 80_000}),
    )
    db_session.add(action)
    db_session.commit()
    monkeypatch.setattr(agent, "get_langfuse_client", lambda: None)

    app = FastAPI()
    app.include_router(agent.router, prefix="/agent")
    app.dependency_overrides[get_db] = lambda: db_session
    response = TestClient(app).post(f"/agent/actions/{action.id}/approve")

    db_session.refresh(product)
    db_session.refresh(action)
    index = db_session.query(models.PricingIndex).filter_by(product_id=product.id).one()
    assert response.status_code == 200
    assert product.guardian_price == 80_000
    assert action.status == "Approved"
    assert index.competitor_index == 100.0
