from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.models import Base

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    if not settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    Base.metadata.create_all(bind=engine)
    # Lightweight additive migrations for existing DBs
    with engine.connect() as conn:
        try:
            if settings.database_url.startswith("sqlite"):
                cols = [r[1] for r in conn.execute(text("PRAGMA table_info(jobs)")).fetchall()]
                if "is_internship" not in cols:
                    conn.execute(text("ALTER TABLE jobs ADD COLUMN is_internship BOOLEAN DEFAULT 0"))
                    conn.commit()
            else:
                conn.execute(
                    text(
                        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_internship BOOLEAN DEFAULT FALSE"
                    )
                )
                conn.commit()
        except Exception:
            conn.rollback()
