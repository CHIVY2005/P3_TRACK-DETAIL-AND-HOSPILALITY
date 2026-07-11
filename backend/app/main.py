import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.agents.shared.runtime_support import shutdown_langfuse
from app.config import settings
from app.db.session import Base, engine
from app.routes import agent, alerts, ingest, pricing, products, scraper, sync
from app.services.daily_scheduler import start_daily_scheduler, stop_daily_scheduler


logger = logging.getLogger(__name__)


Base.metadata.create_all(bind=engine)


def ensure_compat_schema() -> None:
    dialect = engine.dialect.name
    statements = []
    if dialect == "postgresql":
        statements.extend(
            [
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS stock_status VARCHAR(50) DEFAULT 'IN_STOCK';",
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS is_suspicious BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS voucher_details VARCHAR(255);",
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS promo_mechanics VARCHAR(255);",
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS url VARCHAR(500);",
                "ALTER TABLE competitor_prices ADD COLUMN IF NOT EXISTS raw_payload JSONB;",
            ]
        )
    elif dialect == "sqlite":
        statements.extend(
            [
                "ALTER TABLE competitor_prices ADD COLUMN stock_status VARCHAR(50) DEFAULT 'IN_STOCK';",
                "ALTER TABLE competitor_prices ADD COLUMN is_suspicious BOOLEAN DEFAULT 0;",
                "ALTER TABLE competitor_prices ADD COLUMN voucher_details VARCHAR(255);",
                "ALTER TABLE competitor_prices ADD COLUMN promo_mechanics VARCHAR(255);",
                "ALTER TABLE competitor_prices ADD COLUMN url VARCHAR(500);",
                "ALTER TABLE competitor_prices ADD COLUMN raw_payload JSON;",
            ]
        )

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception:
                pass


ensure_compat_schema()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for real-time pricing tracking, competitor index (CPI) calculations and automated price alerts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])
app.include_router(pricing.router, prefix=f"{settings.API_V1_STR}/pricing", tags=["Pricing & CPI"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Alerts"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["Scraper Controls"])
app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["AI Agent Workspace"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingestion"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])


@app.on_event("startup")
def on_startup():
    start_daily_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_daily_scheduler()
    shutdown_langfuse()


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get(f"{settings.API_V1_STR}/health")
def read_health():
    return {
        "status": "healthy",
        "api_base": settings.API_V1_STR,
        "database_url": settings.sqlalchemy_database_uri,
        "fallback_fixture": settings.APIFY_FIXTURE_FALLBACK or settings.APIFY_FALLBACK_TO_FIXTURE,
    }
