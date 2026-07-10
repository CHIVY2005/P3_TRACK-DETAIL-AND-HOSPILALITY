from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import get_db
from app.routes import alerts


def test_alert_feed_orders_business_severity(db_session):
    product = models.Product(
        barcode="ALERT-1",
        name="Alert Product",
        category="Skincare",
        guardian_price=100_000,
        cost_price=60_000,
    )
    db_session.add(product)
    db_session.flush()
    db_session.add_all(
        [
            models.Alert(product_id=product.id, alert_type="Low", message="low", severity="Low"),
            models.Alert(product_id=product.id, alert_type="High", message="high", severity="High"),
            models.Alert(product_id=product.id, alert_type="Medium", message="medium", severity="Medium"),
        ]
    )
    db_session.commit()

    app = FastAPI()
    app.include_router(alerts.router, prefix="/alerts")
    app.dependency_overrides[get_db] = lambda: db_session
    response = TestClient(app).get("/alerts/")

    assert response.status_code == 200
    assert [item["severity"] for item in response.json()] == ["High", "Medium", "Low"]
