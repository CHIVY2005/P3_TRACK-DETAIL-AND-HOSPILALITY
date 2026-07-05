import os
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
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
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"

    # Pricing Alert Configuration
    ALERT_UNDERPRICE_THRESHOLD: float = 0.10  # 10%
    ALERT_OVERPRICE_THRESHOLD: float = 0.10   # 10%

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.USE_SQLITE:
            # SQLite path relative to backend app folder
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(backend_dir, "guardian.db")
            return f"sqlite:///{db_path}"
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

settings = Settings()
