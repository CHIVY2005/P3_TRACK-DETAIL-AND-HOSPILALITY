from app.db import models
from app.services import startup_bootstrap


def test_startup_bootstrap_seeds_empty_demo_catalog(db_session, monkeypatch):
    def fake_seed(db):
        db.add(
            models.Product(
                barcode="BOOTSTRAP-1",
                name="Bootstrap Product",
                category="Skincare",
                guardian_price=100_000,
                cost_price=60_000,
            )
        )
        db.commit()
        return {
            "products": 1,
            "competitor_prices": 6,
            "competitor_links": 6,
        }

    monkeypatch.setattr(startup_bootstrap, "seed_demo_dataset", fake_seed)

    result = startup_bootstrap.ensure_startup_catalog(
        db_session,
        auto_seed=True,
        environment="development",
    )

    assert result["seeded"] is True
    assert result["products"] == 1
    assert db_session.query(models.Product).count() == 1


def test_startup_bootstrap_preserves_existing_catalog(db_session, monkeypatch):
    db_session.add(
        models.Product(
            barcode="EXISTING-1",
            name="Existing Product",
            category="Skincare",
            guardian_price=100_000,
            cost_price=60_000,
        )
    )
    db_session.commit()
    monkeypatch.setattr(
        startup_bootstrap,
        "seed_demo_dataset",
        lambda db: (_ for _ in ()).throw(AssertionError("seed should not run")),
    )

    result = startup_bootstrap.ensure_startup_catalog(
        db_session,
        auto_seed=True,
        environment="development",
    )

    assert result["seeded"] is False
    assert result["products"] == 1


def test_startup_bootstrap_is_disabled_in_production(db_session, monkeypatch):
    monkeypatch.setattr(
        startup_bootstrap,
        "seed_demo_dataset",
        lambda db: (_ for _ in ()).throw(AssertionError("seed should not run")),
    )

    result = startup_bootstrap.ensure_startup_catalog(
        db_session,
        auto_seed=True,
        environment="production",
    )

    assert result["seeded"] is False
    assert result["products"] == 0
    assert "restricted" in result["message"]
