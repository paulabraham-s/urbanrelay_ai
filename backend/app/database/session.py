"""SQLAlchemy engine, session factory, and declarative base.

Default database is zero-setup SQLite. PostgreSQL (optionally with PostGIS)
is fully supported — set DATABASE_URL and run `docker compose up -d` for the
reference PostGIS stack. Models intentionally use portable column types so the
same schema runs on both backends; PostGIS indexes are added opportunistically.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_fks(dbapi_conn, _record):  # pragma: no cover
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("postgresql"):
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS postgis")
        except Exception:  # pragma: no cover - PostGIS is optional
            pass