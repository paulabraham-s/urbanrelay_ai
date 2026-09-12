"""Application configuration.

All values can be overridden through environment variables or a .env file
placed in the backend/ directory (see .env.example at the repo root).
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


def _parse_cors() -> list[str]:
    """Parse CORS_ORIGINS from env var — handles JSON, comma-separated, or empty."""
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        return [str(parsed)]
    except (json.JSONDecodeError, ValueError):
        return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "UrbanRelay AI"
    debug: bool = False

    # Security
    secret_key: str = "urbanrelay-demo-secret-change-me"
    access_token_expire_minutes: int = 720

    # Database. Default is zero-setup SQLite stored next to the backend; switch
    # to PostgreSQL by setting DATABASE_URL and using docker-compose for PostGIS.
    database_url: str = f"sqlite:///{BACKEND_DIR / 'urbanrelay.db'}"

    # CORS — parsed from env var via helper function to avoid pydantic-settings
    # trying json.loads on raw env strings
    cors_origins: list[str] = ["*"]

    # Data locations — resolved relative to this file so they work in any CWD
    geojson_dir: str = str(REPO_ROOT / "data" / "geojson")
    geojson_path: str = str(REPO_ROOT / "data" / "geojson" / "hyderabad_roads.geojson")
    seed_dir: str = str(REPO_ROOT / "data" / "seed")

    # Frontend dist — for serving static files in production
    frontend_dist: str = str(REPO_ROOT / "frontend" / "dist")

    # Simulation defaults
    sim_tick_seconds: float = 1.0       # wall-clock seconds per sim tick at 1x
    sim_default_speed: float = 1.0      # simulation speed multiplier
    sim_seed: int = 42
    sim_reopt_interval: float = 150.0   # sim seconds between AI re-optimizations


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Override cors_origins from env after construction (bypasses pydantic-settings parsing)
    s.cors_origins = _parse_cors()
    return s