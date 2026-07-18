from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.config import AppConfig
from app.database.connection import initialize_database
from app.services.backup_service import BackupService
from app.services.import_service import import_initial_pdf_if_available
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def run(argv: list[str] | None = None) -> int:
    config = AppConfig.from_project()
    config.ensure_directories()
    engine = initialize_database(config.database_url)
    import_initial_pdf_if_available(engine)
    try:
        BackupService(config.database_path, config.backups_dir).ensure_daily_backup()
    except (OSError, ValueError):
        # Un problema de respaldo no debe impedir abrir la operación comercial.
        pass

    qt_app = QApplication(argv or [])
    qt_app.setApplicationName(config.app_name)
    qt_app.setOrganizationName(config.business_name)
    apply_theme(qt_app)

    window = MainWindow(config=config, engine=engine)
    window.show()
    return qt_app.exec()
