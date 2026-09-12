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
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "chrome-extension://*",
        ]
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        return [str(parsed)]
    except (json.JSONDecodeError, ValueError):
        return [o.strip() for o in raw.split(",") if o.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
        env_ignore={"CORS_ORIGINS"},
    )

    app_name: str = "UrbanRelay AI"
    debug: bool = False

    # Security
    secret_key: str = "urbanrelay-demo-secret-change-me"
    access_token_expire_minutes: int = 720

    # Database
    database_url: str = f"sqlite:///{BACKEND_DIR / 'urbanrelay.db'}"

    # CORS — read from env in get_settings(), not via pydantic-settings
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "chrome-extension://*",
    ]

    # Data locations
    geojson_dir: str = str(REPO_ROOT / "data" / "geojson")
    geojson_path: str = str(REPO_ROOT / "data" / "geojson" / "hyderabad_roads.geojson")
    seed_dir: str = str(REPO_ROOT / "data" / "seed")

    # Frontend dist — for serving static files in production
    frontend_dist: str = str(REPO_ROOT / "frontend" / "dist")

    # Simulation defaults
    sim_tick_seconds: float = 1.0
    sim_default_speed: float = 1.0
    sim_seed: int = 42
    sim_reopt_interval: float = 150.0


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.cors_origins = _parse_cors()
    return s
