from __future__ import annotations

from sqlalchemy import Engine, text

SCHEMA_VERSION = 1


def apply_initial_migration(engine: Engine) -> None:
    """Registra la version inicial del esquema creado con SQLAlchemy.

    En esta etapa usamos `create_all` porque la app todavia no tiene datos de usuario.
    La tabla de versiones deja preparado un sistema propio simple para migraciones futuras.
    """
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO schema_migrations (version, name)
                VALUES (:version, :name)
                """
            ),
            {"version": SCHEMA_VERSION, "name": "initial_schema"},
        )
