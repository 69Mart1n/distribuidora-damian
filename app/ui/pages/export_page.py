from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.export_service import ExportService
from app.services.product_service import ProductService
from app.ui.common import button, page_header
from app.ui.dialogs.receipt_preview_dialog import ReceiptPreviewDialog


class ExportPage(QWidget):
    def __init__(self, engine: Engine, exports_dir: Path) -> None:
        super().__init__()
        self._service = ExportService(engine, exports_dir)
        catalog = ProductService(engine)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Exportar precios",
                "Genera listas por proveedor o categoría en PDF, Excel y CSV.",
            )
        )
        panel = QFrame()
        panel.setObjectName("Panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 22, 22, 22)
        form = QFormLayout()
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Todos los proveedores", None)
        for item_id, name in catalog.list_suppliers():
            self.supplier_combo.addItem(name, item_id)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas las categorías", None)
        for item_id, name in catalog.list_categories():
            self.category_combo.addItem(name, item_id)
        self.format_combo = QComboBox()
        self.format_combo.addItem("PDF para imprimir", "pdf")
        self.format_combo.addItem("Excel", "xlsx")
        self.format_combo.addItem("CSV", "csv")
        form.addRow("Proveedor", self.supplier_combo)
        form.addRow("Categoría", self.category_combo)
        form.addRow("Formato", self.format_combo)
        actions = QHBoxLayout()
        generate = button("Generar exportación", "file-output", "PrimaryButton")
        generate.clicked.connect(self._export)
        open_folder = QPushButton("Abrir carpeta de exportaciones")
        open_folder.clicked.connect(lambda: os.startfile(exports_dir))  # type: ignore[attr-defined]
        actions.addWidget(generate)
        actions.addWidget(open_folder)
        actions.addStretch(1)
        panel_layout.addLayout(form)
        panel_layout.addLayout(actions)
        layout.addWidget(panel)
        layout.addStretch(1)

    def _export(self) -> None:
        kwargs = {
            "supplier_id": self.supplier_combo.currentData(),
            "category_id": self.category_combo.currentData(),
        }
        try:
            file_format = self.format_combo.currentData()
            if file_format == "pdf":
                path = self._service.export_wholesale_price_pdf(**kwargs)
                ReceiptPreviewDialog(path, self).exec()
                return
            if file_format == "xlsx":
                path = self._service.export_wholesale_price_excel(**kwargs)
            else:
                path = self._service.export_wholesale_price_csv(**kwargs)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo exportar", str(error))
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Guardar copia", path.name, f"Archivo (*{path.suffix})"
        )
        if destination:
            Path(destination).write_bytes(path.read_bytes())
        os.startfile(path)  # type: ignore[attr-defined]
