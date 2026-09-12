"""Application configuration.

All values can be overridden through environment variables or a .env file
placed in the backend/ directory (see .env.example at the repo root).
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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
    database_url: str = f"sqlite:///{BACKEND_DIR / 'urbanrelay.db'}"

    # CORS — accepts a JSON list or comma-separated string via env var
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "chrome-extension://*",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return ["*"]
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [o.strip() for o in v.split(",") if o.strip()]
        return v

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
    return Settings()