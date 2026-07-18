from __future__ import annotations

import hashlib
import shutil
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class BackupSummary:
    path: Path
    created_at: datetime
    backup_type: str
    size_bytes: int
    verified: bool


class BackupService:
    def __init__(self, database_path: Path, backups_dir: Path) -> None:
        self._database_path = database_path.resolve()
        self._backups_dir = backups_dir.resolve()

    def create_manual_backup(self) -> Path:
        return self.create_backup("manual")

    def create_backup(self, backup_type: str = "manual") -> Path:
        if not self._database_path.exists():
            raise FileNotFoundError("No se encontró la base de datos.")
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        destination = self._backups_dir / f"distribuidora_{backup_type}_{timestamp}.db"
        with (
            closing(sqlite3.connect(self._database_path)) as source,
            closing(sqlite3.connect(destination)) as target,
        ):
            source.backup(target)
        self._verify(destination)
        self._record(destination, backup_type)
        return destination

    def ensure_daily_backup(self) -> Path | None:
        today = datetime.now().date()
        daily = [
            backup
            for backup in self.list_backups()
            if backup.backup_type == "automatic" and backup.created_at.date() == today
        ]
        if daily:
            return None
        path = self.create_backup("automatic")
        self.cleanup_retention()
        return path

    def list_backups(self) -> list[BackupSummary]:
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        rows: list[BackupSummary] = []
        for path in self._backups_dir.glob("*.db"):
            stat = path.stat()
            name = path.stem
            backup_type = "manual"
            for candidate in [
                "automatic",
                "before_import",
                "before_price_update",
                "before_restore",
                "before_migration",
            ]:
                if candidate in name or candidate.replace("before_", "pre_") in name:
                    backup_type = candidate
                    break
            rows.append(
                BackupSummary(
                    path,
                    datetime.fromtimestamp(stat.st_mtime),
                    backup_type,
                    stat.st_size,
                    self._is_valid(path),
                )
            )
        return sorted(rows, key=lambda row: row.created_at, reverse=True)

    def restore_backup(self, source_path: Path) -> None:
        source_path = source_path.resolve()
        if not source_path.exists() or self._verify(source_path) != "ok":
            raise ValueError("El respaldo seleccionado no es valido.")
        self.create_backup("before_restore")
        with (
            closing(sqlite3.connect(source_path)) as source,
            closing(sqlite3.connect(self._database_path)) as target,
        ):
            source.backup(target)
        self._verify(self._database_path)

    def export_backup(self, source_path: Path, destination_dir: Path) -> Path:
        source_path = source_path.resolve()
        if not source_path.exists():
            raise FileNotFoundError("No se encontró el respaldo.")
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / source_path.name
        shutil.copy2(source_path, destination)
        self._verify(destination)
        return destination

    def cleanup_retention(self, daily_days: int = 30, monthly_count: int = 12) -> None:
        backups = [row for row in self.list_backups() if row.backup_type == "automatic"]
        cutoff = datetime.now() - timedelta(days=daily_days)
        old = [row for row in backups if row.created_at < cutoff]
        monthly_to_keep: set[Path] = set()
        seen_months: set[tuple[int, int]] = set()
        for row in old:
            month = (row.created_at.year, row.created_at.month)
            if month not in seen_months and len(seen_months) < monthly_count:
                monthly_to_keep.add(row.path)
                seen_months.add(month)
        for row in old:
            if row.path not in monthly_to_keep:
                row.path.unlink(missing_ok=True)

    def _record(self, path: Path, backup_type: str) -> None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            with closing(sqlite3.connect(self._database_path)) as database:
                database.execute(
                    """
                    INSERT INTO backups
                        (filename, file_path, created_at, backup_type, size_bytes, checksum, status)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 'verified')
                    """,
                    (path.name, str(path), backup_type, path.stat().st_size, digest),
                )
                database.commit()
        except sqlite3.OperationalError:
            pass

    @staticmethod
    def _verify(path: Path) -> str:
        with closing(sqlite3.connect(path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError("La copia de seguridad no superó la verificación de integridad.")
        return result

    @classmethod
    def _is_valid(cls, path: Path) -> bool:
        try:
            return cls._verify(path) == "ok"
        except (OSError, sqlite3.DatabaseError, ValueError):
            return False
