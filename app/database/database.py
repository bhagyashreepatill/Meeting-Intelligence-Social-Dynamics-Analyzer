"""Database connection and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.utils.config import settings

# Configure SQLite engine with appropriate connection parameters
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False
)

# Enable foreign keys and WAL mode for SQLite for high concurrency and relational integrity
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run lightweight migrations."""
    import app.models  # Ensure all models are imported
    Base.metadata.create_all(bind=engine)

    # Safely migrate new columns if using SQLite
    if settings.database_url.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                res = conn.exec_driver_sql("PRAGMA table_info(participants)").fetchall()
                existing_cols = {row[1] for row in res}
                new_cols = [
                    ("employee_id", "VARCHAR(64)"),
                    ("role", "VARCHAR(128)"),
                    ("department", "VARCHAR(128)"),
                    ("responsibilities", "VARCHAR(512)")
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        conn.exec_driver_sql(f"ALTER TABLE participants ADD COLUMN {col_name} {col_type}")
                conn.commit()
        except Exception:
            pass
