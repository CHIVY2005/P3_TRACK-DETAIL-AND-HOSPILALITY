from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.routes import products


def test_static_seed_route_is_not_captured_as_product_id(db_session, monkeypatch):
    monkeypatch.setattr(
        products,
        "seed_demo_dataset",
        lambda db: {
            "products": 200,
            "competitor_prices": 8400,
            "competitor_links": 1200,
            "source": {},
        },
    )

    app = FastAPI()
    app.include_router(products.router, prefix="/products")
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)

    response = client.post("/products/seed-demo")

    assert response.status_code == 201
    assert response.json()["products"] == 200
    assert client.get("/products/not-a-number").status_code == 404
