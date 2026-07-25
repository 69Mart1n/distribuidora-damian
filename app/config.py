from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    app_name: str
    business_name: str
    project_root: Path
    resource_root: Path
    data_dir: Path
    imports_dir: Path
    exports_dir: Path
    backups_dir: Path
    logs_dir: Path
    assets_dir: Path
    database_path: Path

    @classmethod
    def from_project(cls) -> AppConfig:
        embedded_runtime = (
            Path(sys.executable).resolve().parent / "distribuidora-runtime.marker"
        )
        if embedded_runtime.exists():
            resource_root = Path(sys.executable).resolve().parent.parent / "app"
            local_app_data = Path(
                os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
            project_root = local_app_data / "Distribuidora Damian"
        elif getattr(sys, "frozen", False):
            resource_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
            local_app_data = Path(
                os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
            project_root = local_app_data / "Distribuidora Damian"
        else:
            resource_root = Path(__file__).resolve().parents[1]
            project_root = resource_root
        data_dir = project_root / "data"
        return cls(
            app_name="Distribuidora Damián",
            business_name="Distribuidora Damián",
            project_root=project_root,
            resource_root=resource_root,
            data_dir=data_dir,
            imports_dir=data_dir / "imports",
            exports_dir=project_root / "exports",
            backups_dir=project_root / "backups",
            logs_dir=project_root / "logs",
            assets_dir=resource_root / "assets",
            database_path=data_dir / "distribuidora.db",
        )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    def ensure_directories(self) -> None:
        directories = [
            self.data_dir,
            self.imports_dir,
            self.exports_dir,
            self.exports_dir / "boletas",
            self.exports_dir / "listas_precios",
            self.exports_dir / "excel",
            self.backups_dir,
            self.logs_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        seed_database = self.resource_root / "data" / "distribuidora.db"
        if not self.database_path.exists() and seed_database.exists():
            shutil.copy2(seed_database, self.database_path)
