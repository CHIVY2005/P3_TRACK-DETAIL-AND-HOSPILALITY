from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db import models
from app.services.demo_seed import seed_demo_dataset


DEMO_ENVIRONMENTS = {"development", "demo", "local", "test"}


def ensure_startup_catalog(
    db: Session,
    auto_seed: Optional[bool] = None,
    environment: Optional[str] = None,
) -> Dict[str, Any]:
    """Seed a fresh local/demo database once without replacing existing data."""
    enabled = settings.AUTO_SEED_DEMO if auto_seed is None else auto_seed
    current_environment = (environment or settings.ENV).strip().lower()
    existing_products = db.query(models.Product).count()

    status = {
        "enabled": enabled,
        "environment": current_environment,
        "seeded": False,
        "products": existing_products,
        "message": "Existing catalog preserved.",
    }

    if not enabled:
        status["message"] = "Automatic demo seed is disabled."
        return status

    if current_environment not in DEMO_ENVIRONMENTS:
        status["message"] = "Automatic demo seed is restricted to local/demo environments."
        return status

    if existing_products > 0:
        return status

    result = seed_demo_dataset(db)
    return {
        **status,
        "seeded": True,
        "products": result["products"],
        "competitor_prices": result["competitor_prices"],
        "competitor_links": result["competitor_links"],
        "message": "Fresh database initialized with the demo catalog.",
    }
