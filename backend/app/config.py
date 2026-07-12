import json
import os

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# Load env variables from root workspace if they exist
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Guardian Pricing Intelligence Platform"

    # Backwards compatibility / defaults
    ENV: str = "development"

    # Database engine selection
    USE_SQLITE: bool = True

    # Full connection string (Neon/Supabase/etc). If set, overrides the fields below.
    # Accepts either DATABASE_URL or the legacy DB_URL name used in .env.
    DATABASE_URL: str = ""
    DB_URL: str = ""

    # PostgreSQL Database Config
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "guardian_db"

    # Redis Config
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Scraper Settings
    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    # Pricing Alert Configuration
    ALERT_UNDERPRICE_THRESHOLD: float = 0.10  # 10%
    ALERT_OVERPRICE_THRESHOLD: float = 0.10  # 10%
    PRICING_TARGET_SKU_COUNT: int = 200
    PRICING_FRESHNESS_HOURS: int = 24
    AGENT_SCHEDULER_ENABLED: bool = True
    AGENT_SCHEDULE_INTERVAL_SECONDS: int = 86400

    @field_validator("ALERT_UNDERPRICE_THRESHOLD", "ALERT_OVERPRICE_THRESHOLD", mode="before")
    @classmethod
    def parse_float_with_inline_comment(cls, value):
        if isinstance(value, str):
            return float(value.split("#", 1)[0].strip())
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        # Hybrid switch: USE_SQLITE=True forces the fast local file (instant, for demos)
        # even when a remote DB_URL is present. Set USE_SQLITE=False to use Supabase.
        if self.USE_SQLITE:
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(backend_dir, "guardian.db")
            return f"sqlite:///{db_path}"

        # Otherwise a full connection string (Neon/Supabase) wins over the split fields.
        full_url = self.DATABASE_URL or self.DB_URL
        if full_url:
            url = full_url.strip()
            # SQLAlchemy needs the "postgresql://" scheme, not the legacy "postgres://".
            if url.startswith("postgres://"):
                url = "postgresql://" + url[len("postgres://"):]
            # Managed Postgres requires SSL; add it if the URL doesn't mention it.
            if url.startswith("postgresql://") and "sslmode=" not in url:
                url += ("&" if "?" in url else "?") + "sslmode=require"
            return url
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")


settings = Settings()


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
        "custom_instruction": "Toi uu hoa bien loi nhuan dong thoi duy tri kha nang canh tranh cao o kenh Shopee.",
    }


# Don gia (VND) uoc luong cho moi lan cao du lieu tren tung platform.
# Dung de tinh chi phi scrape va luu vao DB.
DEFAULT_SCRAPE_COST_PER_PLATFORM = {
    "Shopee": 300.0,      # Apify (tra phi)
    "Lazada": 300.0,      # Apify (tra phi)
    "Pharmacity": 0.0,    # API JSON cong khai - mien phi
    "Hasaki": 0.0,        # API JSON cong khai - mien phi
    "TikTok Shop": 350.0,
    "GrabMart": 250.0,
}
DEFAULT_SCRAPE_COST_FALLBACK = 250.0


def get_scrape_cost_config() -> dict:
    """Doc bang don gia scrape tu config.json, mac dinh la bang tren."""
    cfg = get_agent_config()
    table = cfg.get("scrape_cost_per_platform")
    if isinstance(table, dict) and table:
        return table
    return DEFAULT_SCRAPE_COST_PER_PLATFORM


def get_scrape_cost_for(platform: str) -> float:
    table = get_scrape_cost_config()
    return float(table.get(platform, DEFAULT_SCRAPE_COST_FALLBACK))


def save_agent_config(config_data: dict):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(backend_dir, "data", "config.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)
