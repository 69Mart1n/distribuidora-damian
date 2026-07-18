from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.backup_service import BackupService
from app.services.price_service import PriceChangePreview, PriceService
from app.services.product_service import ProductService
from app.ui.common import button, configure_table, page_header
from app.utils.money import format_money


class PriceUpdatePage(QWidget):
    def __init__(self, engine: Engine, database_path: Path, backups_dir: Path) -> None:
        super().__init__()
        self._service = PriceService(engine)
        self._catalog = ProductService(engine)
        self._backup = BackupService(database_path, backups_dir)
        self._changes: list[PriceChangePreview] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Actualización de precios",
                "Previsualiza cambios masivos, ajusta filas y deshaz lotes aplicados.",
            )
        )
        controls = QHBoxLayout()
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Todos los proveedores", None)
        for item_id, name in self._catalog.list_suppliers():
            self.supplier_combo.addItem(name, item_id)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas las categorías", None)
        for item_id, name in self._catalog.list_categories():
            self.category_combo.addItem(name, item_id)
        self.operation_combo = QComboBox()
        self.operation_combo.addItem("Aumentar porcentaje", "increase_percentage")
        self.operation_combo.addItem("Disminuir porcentaje", "decrease_percentage")
        self.operation_combo.addItem("Sumar monto fijo", "add_fixed_amount")
        self.operation_combo.addItem("Restar monto fijo", "subtract_fixed_amount")
        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0.01, 1000000)
        self.value_input.setDecimals(2)
        self.value_input.setValue(5)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Motivo del cambio")
        preview = button("Vista previa", "eye", "AccentButton")
        preview.clicked.connect(self._preview)
        controls.addWidget(self.supplier_combo)
        controls.addWidget(self.category_combo)
        controls.addWidget(self.operation_combo)
        controls.addWidget(self.value_input)
        controls.addWidget(self.description_input, 1)
        controls.addWidget(preview)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Aplicar", "Código", "Producto", "Presentación", "Anterior", "Nuevo", "Diferencia"]
        )
        configure_table(self.table, 2)
        footer = QHBoxLayout()
        self.summary = QLabel("Genera una vista previa para comenzar.")
        history = button("Historial y deshacer", "history")
        history.clicked.connect(self._history)
        apply_action = button("Aplicar lote", "save", "PrimaryButton")
        apply_action.clicked.connect(self._apply)
        footer.addWidget(self.summary)
        footer.addStretch(1)
        footer.addWidget(history)
        footer.addWidget(apply_action)
        layout.addLayout(controls)
        layout.addWidget(self.table, 1)
        layout.addLayout(footer)

    def _preview(self) -> None:
        try:
            self._changes = self._service.preview(
                operation=str(self.operation_combo.currentData()),
                value=Decimal(str(self.value_input.value())),
                supplier_id=self.supplier_combo.currentData(),
                category_id=self.category_combo.currentData(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "No se pudo calcular", str(error))
            return
        self.table.setRowCount(len(self._changes))
        for row, change in enumerate(self._changes):
            selected = QTableWidgetItem()
            selected.setCheckState(Qt.CheckState.Checked)
            selected.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, selected)
            for column, value in enumerate(
                [change.code, change.product, change.presentation, format_money(change.old_price)],
                1,
            ):
                self.table.setItem(row, column, QTableWidgetItem(value))
            new_price = QSpinBox()
            new_price.setRange(1, 99_999_999)
            new_price.setValue(int(change.new_price))
            new_price.setPrefix("$ ")
            new_price.setGroupSeparatorShown(True)
            self.table.setCellWidget(row, 5, new_price)
            self.table.setItem(row, 6, QTableWidgetItem(format_money(change.difference)))
        self.summary.setText(f"{len(self._changes)} productos en la vista previa")

    def _apply(self) -> None:
        if not self._changes:
            QMessageBox.warning(self, "Vista previa requerida", "Genera una vista previa primero.")
            return
        for row, change in enumerate(self._changes):
            change.included = self.table.item(row, 0).checkState() == Qt.CheckState.Checked
            editor = self.table.cellWidget(row, 5)
            if isinstance(editor, QSpinBox):
                change.new_price = Decimal(editor.value())
        answer = QMessageBox.question(
            self,
            "Confirmar lote",
            "Se creará un respaldo y se aplicarán los precios seleccionados. ¿Continuar?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._backup.create_backup("before_price_update")
            result = self._service.apply(
                self._changes,
                description=self.description_input.text(),
                operation=str(self.operation_combo.currentData()),
                value=Decimal(str(self.value_input.value())),
                target_type="filtered",
                supplier_id=self.supplier_combo.currentData(),
                category_id=self.category_combo.currentData(),
            )
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "No se pudo aplicar", str(error))
            return
        QMessageBox.information(
            self, "Precios actualizados", f"Se actualizaron {result.products_affected} productos."
        )
        self._changes.clear()
        self.table.setRowCount(0)
        self.summary.setText("Lote aplicado correctamente.")

    def _history(self) -> None:
        batches = self._service.list_batches()
        active = [batch for batch in batches if batch.active]
        if not active:
            QMessageBox.information(self, "Historial", "No hay lotes activos para deshacer.")
            return
        labels = [
            f"{batch.applied_at:%d/%m/%Y %H:%M} · {batch.description} · "
            f"{batch.products_affected} productos"
            for batch in active
        ]
        from PySide6.QtWidgets import QInputDialog

        selected, accepted = QInputDialog.getItem(
            self, "Deshacer lote", "Selecciona el lote:", labels, 0, False
        )
        if not accepted:
            return
        index = labels.index(selected)
        count = self._service.revert_batch(active[index].id)
        QMessageBox.information(self, "Lote deshecho", f"Se restauraron {count} precios.")
