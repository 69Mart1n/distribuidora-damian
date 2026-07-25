from __future__ import annotations

import sys

from app.config import AppConfig


def test_frozen_config_copies_seed_database_to_local_app_data(tmp_path, monkeypatch) -> None:
    resource_root = tmp_path / "resources"
    seed_database = resource_root / "data" / "distribuidora.db"
    seed_database.parent.mkdir(parents=True)
    seed_database.write_bytes(b"seed database")

    local_app_data = tmp_path / "local"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(resource_root), raising=False)

    config = AppConfig.from_project()
    config.ensure_directories()

    assert config.project_root == local_app_data / "Distribuidora Damian"
    assert config.assets_dir == resource_root / "assets"
    assert config.database_path.read_bytes() == b"seed database"


def test_embedded_runtime_uses_installed_resources(tmp_path, monkeypatch) -> None:
    runtime_dir = tmp_path / "installation" / "runtime"
    runtime_dir.mkdir(parents=True)
    marker = runtime_dir / "distribuidora-runtime.marker"
    marker.touch()
    installed_app = runtime_dir.parent / "app"

    local_app_data = tmp_path / "local"
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(sys, "executable", str(runtime_dir / "pythonw.exe"))

    config = AppConfig.from_project()

    assert config.resource_root == installed_app
    assert config.project_root == local_app_data / "Distribuidora Damian"
    assert config.database_path == local_app_data / "Distribuidora Damian" / "data" / "distribuidora.db"
