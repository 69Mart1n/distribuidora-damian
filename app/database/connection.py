from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.migrations.initial import apply_initial_migration
from app.database.migrations.professional import apply_professional_migration
from app.database.models import Base, Settings
from app.database.seed import seed_initial_data


def build_engine(database_url: str) -> Engine:
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


def initialize_database(database_url: str) -> Engine:
    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    apply_initial_migration(engine)
    apply_professional_migration(engine)
    session_factory = build_session_factory(engine)
    with session_scope(session_factory) as session:
        seed_initial_data(session)
        settings = session.get(Settings, 1)
        if settings is not None and settings.next_receipt_number < 500:
            settings.next_receipt_number = 500
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
