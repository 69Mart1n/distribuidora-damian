from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, inspect, text

SCHEMA_VERSION = 2


def apply_professional_migration(engine: Engine) -> None:
    if _is_applied(engine):
        return
    backup_path = _backup_database(engine)
    source_path = Path(engine.url.database).resolve() if engine.url.database else None
    logo_path = (
        source_path.parent.parent / "assets" / "logo" / "distribuidora_damian.png"
        if source_path
        else None
    )
    with engine.begin() as connection:
        _add_missing_columns(engine, connection)
        removed_test_receipts = connection.execute(
            text(
                """
                SELECT count(*) FROM receipts
                WHERE receipt_code IN ('BD-000001', 'BD-000500')
                  AND lower(customer_name_snapshot) IN ('holaaa', 'noraa')
                """
            )
        ).scalar_one()
        connection.execute(
            text(
                """
                DELETE FROM receipt_items
                WHERE receipt_id IN (
                    SELECT id FROM receipts
                    WHERE receipt_code IN ('BD-000001', 'BD-000500')
                      AND lower(customer_name_snapshot) IN ('holaaa', 'noraa')
                )
                """
            )
        )
        connection.execute(
            text(
                """
                DELETE FROM receipts
                WHERE receipt_code IN ('BD-000001', 'BD-000500')
                  AND lower(customer_name_snapshot) IN ('holaaa', 'noraa')
                """
            )
        )
        if removed_test_receipts:
            connection.execute(
                text(
                    """
                    UPDATE settings
                    SET next_receipt_number = CASE
                        WHEN next_receipt_number < 501 THEN 501
                        ELSE next_receipt_number
                    END
                    WHERE id = 1
                    """
                )
            )
        _merge_supplier(connection, "Grinor S.A", "Grinor")
        _merge_supplier(connection, "SADENIR S.A", "Sadenir")
        connection.execute(
            text(
                """
                UPDATE settings
                SET business_name = :business_name,
                    business_logo_path = COALESCE(NULLIF(business_logo_path, ''), :logo_path)
                WHERE id = 1
                """
            ),
            {
                "business_name": "Distribuidora Damián",
                "logo_path": str(logo_path) if logo_path else None,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO schema_migrations (version, name)
                VALUES (:version, :name)
                """
            ),
            {"version": SCHEMA_VERSION, "name": "professional_system"},
        )
        if backup_path is not None:
            connection.execute(
                text(
                    """
                    INSERT INTO backups
                        (filename, file_path, created_at, backup_type, size_bytes, checksum, status)
                    VALUES
                        (:filename, :file_path, CURRENT_TIMESTAMP, 'before_migration',
                         :size_bytes, :checksum, 'verified')
                    """
                ),
                {
                    "filename": backup_path.name,
                    "file_path": str(backup_path),
                    "size_bytes": backup_path.stat().st_size,
                    "checksum": hashlib.sha256(backup_path.read_bytes()).hexdigest(),
                },
            )


def _is_applied(engine: Engine) -> bool:
    with engine.connect() as connection:
        return bool(
            connection.execute(
                text("SELECT count(*) FROM schema_migrations WHERE version = :version"),
                {"version": SCHEMA_VERSION},
            ).scalar_one()
        )


def _backup_database(engine: Engine) -> Path | None:
    database = engine.url.database
    if not database:
        return None
    source_path = Path(database).resolve()
    if not source_path.exists() or source_path.stat().st_size == 0:
        return None
    with engine.connect() as connection:
        has_business_data = connection.execute(text("SELECT count(*) FROM products")).scalar_one()
    if not has_business_data:
        return None
    backups_dir = source_path.parent.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    destination = backups_dir / f"pre_migracion_v2_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
    with (
        closing(sqlite3.connect(source_path)) as source,
        closing(sqlite3.connect(destination)) as target,
    ):
        source.backup(target)
    with closing(sqlite3.connect(destination)) as check:
        if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            destination.unlink(missing_ok=True)
            raise RuntimeError("No se pudo verificar el respaldo previo a la migracion.")
    return destination


def _add_missing_columns(engine: Engine, connection) -> None:  # type: ignore[no-untyped-def]
    inspector = inspect(engine)
    settings_columns = {column["name"] for column in inspector.get_columns("settings")}
    receipt_columns = {column["name"] for column in inspector.get_columns("receipts")}
    settings_additions = {
        "backup_retention_days": "INTEGER NOT NULL DEFAULT 30",
        "monthly_retention_count": "INTEGER NOT NULL DEFAULT 12",
        "exports_path": "VARCHAR(500)",
        "backups_path": "VARCHAR(500)",
        "theme": "VARCHAR(30) NOT NULL DEFAULT 'light'",
    }
    for column, definition in settings_additions.items():
        if column not in settings_columns:
            connection.execute(text(f"ALTER TABLE settings ADD COLUMN {column} {definition}"))
    if "cancellation_reason" not in receipt_columns:
        connection.execute(text("ALTER TABLE receipts ADD COLUMN cancellation_reason TEXT"))


def _merge_supplier(connection, duplicate_name: str, canonical_name: str) -> None:  # type: ignore[no-untyped-def]
    duplicate = connection.execute(
        text("SELECT id FROM suppliers WHERE name = :name"), {"name": duplicate_name}
    ).scalar_one_or_none()
    canonical = connection.execute(
        text("SELECT id FROM suppliers WHERE name = :name"), {"name": canonical_name}
    ).scalar_one_or_none()
    if duplicate is None or canonical is None or duplicate == canonical:
        return
    connection.execute(
        text("UPDATE products SET supplier_id = :canonical WHERE supplier_id = :duplicate"),
        {"canonical": canonical, "duplicate": duplicate},
    )
    connection.execute(
        text("UPDATE brands SET supplier_id = :canonical WHERE supplier_id = :duplicate"),
        {"canonical": canonical, "duplicate": duplicate},
    )
    connection.execute(text("DELETE FROM suppliers WHERE id = :id"), {"id": duplicate})
