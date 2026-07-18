from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.backup_service import BackupService, BackupSummary
from app.ui.common import button, configure_table, page_header


class BackupsPage(QWidget):
    def __init__(self, database_path: Path, backups_dir: Path) -> None:
        super().__init__()
        self._service = BackupService(database_path, backups_dir)
        self._backups: list[BackupSummary] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Respaldos",
                "Crea, verifica, exporta y restaura copias seguras de la base de datos.",
            )
        )
        actions = QHBoxLayout()
        create = button("Crear respaldo", "database-backup", "PrimaryButton")
        create.clicked.connect(self._create)
        export = button("Exportar copia", "file-output")
        export.clicked.connect(self._export)
        restore = button("Restaurar", "rotate-ccw", "DangerButton")
        restore.clicked.connect(self._restore)
        actions.addWidget(create)
        actions.addWidget(export)
        actions.addWidget(restore)
        actions.addStretch(1)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Archivo", "Fecha", "Tipo", "Tamaño", "Integridad"])
        configure_table(self.table, 0)
        layout.addLayout(actions)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self._backups = self._service.list_backups()
        self.table.setRowCount(len(self._backups))
        for row, backup in enumerate(self._backups):
            values = [
                backup.path.name,
                backup.created_at.strftime("%d/%m/%Y %H:%M"),
                backup.backup_type.replace("_", " ").title(),
                f"{backup.size_bytes / 1024:.0f} KB",
                "Verificado" if backup.verified else "Con error",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)

    def _selected(self) -> BackupSummary | None:
        row = self.table.currentRow()
        return self._backups[row] if 0 <= row < len(self._backups) else None

    def _create(self) -> None:
        try:
            path = self._service.create_manual_backup()
        except OSError as error:
            QMessageBox.warning(self, "No se pudo crear", str(error))
            return
        self.refresh()
        QMessageBox.information(self, "Respaldo creado", f"Copia verificada:\n{path}")

    def _export(self) -> None:
        backup = self._selected()
        if backup is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un respaldo.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de destino")
        if folder:
            self._service.export_backup(backup.path, Path(folder))
            QMessageBox.information(
                self, "Copia exportada", "El respaldo fue copiado y verificado."
            )

    def _restore(self) -> None:
        backup = self._selected()
        if backup is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un respaldo.")
            return
        answer = QMessageBox.warning(
            self,
            "Confirmar restauración",
            "La base actual se respaldará antes de restaurar. "
            "La aplicación deberá reiniciarse. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._service.restore_backup(backup.path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo restaurar", str(error))
            return
        QMessageBox.information(
            self, "Restauración completa", "La base fue restaurada. Reinicia la aplicación."
        )
