from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.agents.shared.runtime_support import shutdown_langfuse
from app.db.session import engine, Base
from app.routes import products, pricing, alerts, scraper, agent, sync
from app.services.daily_scheduler import start_daily_scheduler, stop_daily_scheduler
from app.services.db_keepalive import start_db_keepalive, stop_db_keepalive

# Create database tables automatically for the hackathon environment.
# This ensures that once the user runs the project, the tables are auto-created.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for real-time pricing tracking, competitor index (CPI) calculations and automated price alerts.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration - allow all origins for easy hackathon integration,
# but can be restricted using env variables.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Register API Routers
app.include_router(products.router, prefix=f"{settings.API_V1_STR}/products", tags=["Products"])
app.include_router(pricing.router, prefix=f"{settings.API_V1_STR}/pricing", tags=["Pricing & CPI"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["Alerts"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_STR}/scraper", tags=["Scraper Controls"])
app.include_router(agent.router, prefix=f"{settings.API_V1_STR}/agent", tags=["AI Agent Workspace"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])


@app.on_event("startup")
def on_startup():
    start_db_keepalive()
    start_daily_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_db_keepalive()
    stop_daily_scheduler()
    shutdown_langfuse()

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
        "version": "1.0.0"
    }
