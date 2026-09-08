"""Drop all demo tables so the environment can be reseeded from scratch.

Run from repo root:
    python backend/scripts/reset_demo.py
then:
    python backend/scripts/seed_demo.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.database.session import Base, engine, init_db  # noqa: E402


def main() -> None:
    import app.models.entities  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    init_db()
    print("Database reset. Run `python backend/scripts/seed_demo.py` to reseed.")


if __name__ == "__main__":
    main()