import os
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_ENV_PATH = os.path.join(ROOT_DIR, ".env")
BACKEND_ENV_PATH = os.path.join(BACKEND_DIR, ".env")

# Load root defaults first, then let backend/.env override for demo/runtime safety.
if os.path.exists(ROOT_ENV_PATH):
    load_dotenv(ROOT_ENV_PATH)
if os.path.exists(BACKEND_ENV_PATH):
    load_dotenv(BACKEND_ENV_PATH, override=True)
if not os.path.exists(ROOT_ENV_PATH) and not os.path.exists(BACKEND_ENV_PATH):
    load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Guardian Pricing Intelligence Platform"
    
    # Backwards compatibility / defaults
    ENV: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8001
    
    DATABASE_URL: str
    
    # Redis Config
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Scraper Settings
    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    
    # --- Scraper Provider Toggle ---
    # Values: "apify" (default) | "brightdata" | "zenrows"
    SCRAPER_PROVIDER: str = "apify"

    # --- Apify Actor IDs (one per platform) ---
    APIFY_ACTOR_SHOPEE: str = "xtracto/shopee-scraper"
    APIFY_ACTOR_LAZADA: str = "xtracto/lazada-scraper"
    APIFY_ACTOR_TIKTOK: str = "xtracto/tiktok-scraper"
    APIFY_ACTOR_GRABMART: str = "tanduy.work/garbmart-scarper"
    APIFY_ACTOR_HASAKI: str = "tanduy.work/hasaki-scraper"
    APIFY_ACTOR_PHARMACITY: str = "tanduy.work/pharmacity-scraper "

    # Legacy aliases (backward compat)
    HASAKI_SCRAPER_ACTOR_ID: str = "xtracto/hasaki-scraper"
    HASAKI_SEARCH_ACTOR_ID: str = "hasaki-search-actor-id"

    # --- Fallback Fixture ---
    APIFY_FIXTURE_FALLBACK: bool = True
    APIFY_FIXTURE_PATH: str = "backend/data/apify_fallback_fixture.json"
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Pricing Alert Configuration
    ALERT_UNDERPRICE_THRESHOLD: float = 0.10  # 10%
    ALERT_OVERPRICE_THRESHOLD: float = 0.10   # 10%

    @property
    def sqlalchemy_database_uri(self) -> str:
        return self.DATABASE_URL

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def frontend_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

settings = Settings()

# Platform → Actor ID mapping for the orchestrator
_PLATFORM_ACTOR_MAP = {
    "shopee": settings.APIFY_ACTOR_SHOPEE,
    "lazada": settings.APIFY_ACTOR_LAZADA,
    "tiktok": settings.APIFY_ACTOR_TIKTOK,
    "tiktok_shop": settings.APIFY_ACTOR_TIKTOK,
    "grabmart": settings.APIFY_ACTOR_GRABMART,
    "hasaki": settings.APIFY_ACTOR_HASAKI,
    "pharmacity": settings.APIFY_ACTOR_PHARMACITY,
}


def get_actor_id_for_platform(platform: str) -> str:
    """Resolve the Apify Actor ID for a given platform name."""
    key = platform.lower().strip()
    actor_id = _PLATFORM_ACTOR_MAP.get(key)
    if actor_id is None:
        raise ValueError(f"No Apify Actor configured for platform '{platform}'")
    return actor_id


import json

def get_agent_config() -> dict:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(backend_dir, "data", "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "underprice_threshold": 0.10,
        "overprice_threshold": 0.10,
        "min_margin": 0.15,
        "custom_instruction": "Tối ưu hóa biên lợi nhuận đồng thời duy trì khả năng cạnh tranh cao ở kênh Shopee."
    }

def save_agent_config(config_data: dict):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(backend_dir, "data", "config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
