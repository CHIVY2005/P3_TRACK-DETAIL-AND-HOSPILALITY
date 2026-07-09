import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import engine, SessionLocal
from app.db.models import Base
from app.routes import products, pricing, alerts, scraper, agent, sync, ingest
from app.routes.sync import execute_bulk_sync

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
except ImportError:  # pragma: no cover - startup fallback for demo environments
    AsyncIOScheduler = None

# Create database tables automatically for the hackathon environment.
# This ensures that once the user runs the project, the tables are auto-created.
Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler() if AsyncIOScheduler else None

async def scheduled_bulk_sync():
    db = SessionLocal()
    try:
        await execute_bulk_sync(db)
    except Exception as e:
        logger.error(f"Scheduled sync job failed: {e}")
    finally:
        db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for real-time pricing tracking, competitor index (CPI) calculations and automated price alerts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    if scheduler is None:
        logger.warning("APScheduler is not installed; scheduled bulk sync is disabled.")
        return

    scheduler.add_job(
        scheduled_bulk_sync,
        'interval',
        hours=2,
        id='automated_bulk_sync',
        replace_existing=True
    )
    scheduler.start()

# CORS configuration - allow all origins for easy hackathon integration,
# but can be restricted using env variables.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])
app.include_router(pricing.router, prefix=f"{settings.API_V1_STR}/pricing", tags=["Pricing & CPI"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Alerts"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["Scraper Controls"])
app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["AI Agent Workspace"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_STR}/ingest", tags=["Ingestion"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])


@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get(f"{settings.API_V1_STR}/health")
def read_health():
    return {
        "status": "healthy",
        "api_base": settings.API_V1_STR,
        "database_url": settings.DATABASE_URL,
        "fallback_fixture": settings.APIFY_FIXTURE_FALLBACK,
    }
