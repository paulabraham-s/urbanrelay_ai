"""Application configuration.

All values can be overridden through environment variables or a .env file
placed in the backend/ directory (see .env.example at the repo root).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "UrbanRelay AI"
    debug: bool = False

    # Security
    secret_key: str = "urbanrelay-demo-secret-change-me"
    access_token_expire_minutes: int = 720

    # Database. Default is zero-setup SQLite stored next to the backend; switch
    # to PostgreSQL by setting DATABASE_URL and using docker-compose for PostGIS.
    # Absolute path so the default works regardless of the working directory.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'urbanrelay.db'}"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "chrome-extension://*",
    ]

    # Data locations
    geojson_dir: str = str(REPO_ROOT / "data" / "geojson")
    geojson_path: str = str(REPO_ROOT / "data" / "geojson" / "hyderabad_roads.geojson")
    seed_dir: str = str(REPO_ROOT / "data" / "seed")

    # Simulation defaults
    sim_tick_seconds: float = 1.0       # wall-clock seconds per sim tick at 1x
    sim_default_speed: float = 1.0      # simulation speed multiplier
    sim_seed: int = 42
    sim_reopt_interval: float = 150.0   # sim seconds between AI re-optimizations


@lru_cache
def get_settings() -> Settings:
    return Settings()