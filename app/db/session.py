from collections.abc import Generator

from sqlalchemy import event, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from pgvector.psycopg import register_vector


def build_engine(database_url: str):
    engine = create_engine(database_url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _register_vector(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        register_vector(dbapi_connection)

    return engine


engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
