from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.backup_service import BackupService
from app.services.import_service import ImportPreview, PriceListImportService
from app.ui.common import button, configure_table, page_header
from app.utils.money import format_money


class ImportPage(QWidget):
    def __init__(
        self,
        engine: Engine,
        imports_dir: Path,
        database_path: Path,
        backups_dir: Path,
    ) -> None:
        super().__init__()
        self._service = PriceListImportService(engine, imports_dir)
        self._backup = BackupService(database_path, backups_dir)
        self._preview: ImportPreview | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Importar lista",
                "Carga PDF, Excel o CSV, revisa coincidencias y decide qué filas confirmar.",
            )
        )
        toolbar = QHBoxLayout()
        choose = button("Seleccionar archivo", "file-input", "PrimaryButton")
        choose.clicked.connect(self._choose)
        self.file_label = QLabel("Ningún archivo seleccionado")
        toolbar.addWidget(choose)
        toolbar.addWidget(self.file_label, 1)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Importar", "Fila", "Proveedor", "Producto", "Presentación", "Precio", "Acción"]
        )
        configure_table(self.table, 3)
        self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        footer = QHBoxLayout()
        self.summary = QLabel("Selecciona un archivo para generar la vista previa.")
        confirm = button("Confirmar importación", "save", "AccentButton")
        confirm.clicked.connect(self._commit)
        footer.addWidget(self.summary)
        footer.addStretch(1)
        footer.addWidget(confirm)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)
        layout.addLayout(footer)

    def _choose(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar lista de precios",
            "",
            "Listas de precios (*.pdf *.xlsx *.csv)",
        )
        if not selected:
            return
        try:
            self._preview = self._service.preview_file(Path(selected))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo leer", str(error))
            return
        self.file_label.setText(Path(selected).name)
        self._render()

    def _render(self) -> None:
        if self._preview is None:
            return
        self.table.setRowCount(len(self._preview.rows))
        for row, item in enumerate(self._preview.rows):
            check = QTableWidgetItem()
            check.setCheckState(Qt.CheckState.Checked if item.selected else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)
            values = [
                str(item.row_number),
                item.supplier,
                item.name,
                item.presentation,
                format_money(item.price),
                {"create": "Crear", "update": "Actualizar", "invalid": "Revisar"}[item.action],
            ]
            for column, value in enumerate(values, 1):
                cell = QTableWidgetItem(value)
                if column in {1, 6}:
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if item.error:
                    cell.setToolTip(item.error)
                self.table.setItem(row, column, cell)
        create_count = sum(row.action == "create" for row in self._preview.rows)
        update_count = sum(row.action == "update" for row in self._preview.rows)
        invalid_count = sum(row.action == "invalid" for row in self._preview.rows)
        self.summary.setText(
            f"{len(self._preview.rows)} filas · {create_count} nuevas · "
            f"{update_count} coincidencias · {invalid_count} para revisar"
        )

    def _commit(self) -> None:
        if self._preview is None:
            QMessageBox.warning(self, "Archivo requerido", "Selecciona un archivo primero.")
            return
        try:
            for row_index, row in enumerate(self._preview.rows):
                row.selected = self.table.item(row_index, 0).checkState() == Qt.CheckState.Checked
                row.supplier = self.table.item(row_index, 2).text().strip()
                row.name = self.table.item(row_index, 3).text().strip()
                row.presentation = self.table.item(row_index, 4).text().strip()
                price_text = self.table.item(row_index, 5).text().replace("$", "").replace(".", "")
                row.price = Decimal(price_text.strip()) if price_text.strip() else None
                if row.price is not None and row.price != row.price.to_integral_value():
                    raise ValueError(f"La fila {row.row_number} tiene un precio con centavos.")
            self._backup.create_backup("before_import")
            result = self._service.commit_preview(self._preview)
        except (InvalidOperation, OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo importar", str(error))
            return
        QMessageBox.information(
            self,
            "Importación terminada",
            f"Nuevos: {result.created}\nActualizados: {result.updated}\nOmitidos: {result.skipped}",
        )
        self._preview = None
        self.table.setRowCount(0)
        self.file_label.setText("Ningún archivo seleccionado")
