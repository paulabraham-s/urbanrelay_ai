"""Test configuration.

Uses an isolated SQLite database so tests never touch the dev database.
DATABASE_URL must be set before any app module import (settings are cached).
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent

os.environ["DATABASE_URL"] = f"sqlite:///{ROOT / 'test_urbanrelay.db'}"

sys.path.insert(0, str(BACKEND))


def pytest_configure(config):
    from app.database.session import init_db

    init_db()

    # seed the demo environment into the test database
    from scripts.seed_demo import main as seed_main

    seed_main()


def pytest_unconfigure(config):
    db_path = ROOT / "test_urbanrelay.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass