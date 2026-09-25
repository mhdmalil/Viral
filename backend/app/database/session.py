from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def ensure_schema() -> None:
    """Add columns create_all will not attach to an existing SQLite file."""
    if not settings.database_url.startswith("sqlite"):
        return
    additions = (
        ("projects", "caption_style", "VARCHAR(40) DEFAULT 'classic'"),
        ("projects", "caption_position", "VARCHAR(40) DEFAULT 'lower'"),
        ("projects", "folder_path", "VARCHAR(1000)"),
        ("projects", "reframe_enabled", "INTEGER DEFAULT 0"),
        ("projects", "branding_json", "TEXT DEFAULT '{}'"),
        ("clips", "download_count", "INTEGER DEFAULT 0"),
        ("clips", "removed_from_project", "INTEGER DEFAULT 0"),
        ("clips", "origin_project_name", "VARCHAR(200)"),
        ("processing_jobs", "source_id", "INTEGER"),
    )
    with engine.begin() as conn:
        for table, column, ddl in additions:
            names = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in names:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
