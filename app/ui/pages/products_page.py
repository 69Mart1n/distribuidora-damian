from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.product_service import ProductService, ProductSummary
from app.ui.common import button, configure_table, page_header, search_field
from app.utils.money import format_money


class ProductsPage(QWidget):
    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._service = ProductService(engine)
        self._products: list[ProductSummary] = []
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Productos",
                "Edita precios enteros, filtra el catálogo y revisa el historial de cambios.",
            )
        )
        filters = QHBoxLayout()
        self.search_input = search_field("Nombre, código, presentación o proveedor")
        self.search_input.textChanged.connect(self.refresh)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Todos los proveedores", None)
        for supplier_id, name in self._service.list_suppliers():
            self.supplier_combo.addItem(name, supplier_id)
        self.supplier_combo.currentIndexChanged.connect(self.refresh)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Todas las categorías", None)
        for category_id, name in self._service.list_categories():
            self.category_combo.addItem(name, category_id)
        self.category_combo.currentIndexChanged.connect(self.refresh)
        self.no_price_check = QCheckBox("Sin precio")
        self.no_price_check.toggled.connect(self.refresh)
        self.inactive_check = QCheckBox("Inactivos")
        self.inactive_check.toggled.connect(self.refresh)
        filters.addWidget(self.search_input, 2)
        filters.addWidget(self.supplier_combo)
        filters.addWidget(self.category_combo)
        filters.addWidget(self.no_price_check)
        filters.addWidget(self.inactive_check)
        actions = QHBoxLayout()
        edit_action = button("Editar", "pencil")
        edit_action.clicked.connect(self._edit_selected)
        history_action = button("Historial de precio", "history")
        history_action.clicked.connect(self._show_history)
        duplicate_action = button("Duplicar", "copy")
        duplicate_action.clicked.connect(self._duplicate)
        self.active_action = button("Desactivar", "ban", "DangerButton")
        self.active_action.clicked.connect(self._toggle_active)
        new_action = button("Nuevo producto", "plus", "PrimaryButton")
        new_action.clicked.connect(self._open_new_product_dialog)
        actions.addWidget(edit_action)
        actions.addWidget(history_action)
        actions.addWidget(duplicate_action)
        actions.addWidget(self.active_action)
        actions.addStretch(1)
        actions.addWidget(new_action)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Código", "Producto", "Presentación", "Proveedor", "Categoría", "Precio", "Estado"]
        )
        configure_table(self.table, 1)
        self.table.doubleClicked.connect(self._edit_selected)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        layout.addLayout(filters)
        layout.addLayout(actions)
        layout.addWidget(self.table, 1)

    def refresh(self) -> None:
        self._products = self._service.list_products(
            self.search_input.text(),
            supplier_id=self.supplier_combo.currentData(),
            category_id=self.category_combo.currentData(),
            include_inactive=self.inactive_check.isChecked(),
            only_without_price=self.no_price_check.isChecked(),
        )
        self.table.setRowCount(len(self._products))
        for row, product in enumerate(self._products):
            state = (
                "Inactivo"
                if not product.active
                else "Sin precio"
                if product.requires_review
                else "Activo"
            )
            values = [
                product.code,
                product.name,
                product.presentation,
                product.supplier,
                product.category,
                format_money(product.wholesale_price),
                state,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, product.id)
                if column == 5:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)
        self._selection_changed()

    def _selected_product(self) -> ProductSummary | None:
        row = self.table.currentRow()
        return self._products[row] if 0 <= row < len(self._products) else None

    def _selection_changed(self) -> None:
        product = self._selected_product()
        self.active_action.setText("Activar" if product and not product.active else "Desactivar")

    def _edit_selected(self) -> None:
        product = self._selected_product()
        if product is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un producto.")
            return
        if ProductDialog(self._service, self, product).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _open_new_product_dialog(self) -> None:
        if ProductDialog(self._service, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _duplicate(self) -> None:
        product = self._selected_product()
        if product is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un producto.")
            return
        self._service.duplicate_product(product.id)
        self.refresh()

    def _toggle_active(self) -> None:
        product = self._selected_product()
        if product is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un producto.")
            return
        self._service.set_active(product.id, not product.active)
        self.refresh()

    def _show_history(self) -> None:
        product = self._selected_product()
        if product is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un producto.")
            return
        ProductHistoryDialog(self._service, product, self).exec()


class ProductDialog(QDialog):
    def __init__(
        self,
        service: ProductService,
        parent: QWidget | None = None,
        product: ProductSummary | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._product = product
        self.setWindowTitle("Editar producto" if product else "Nuevo producto")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        form = QFormLayout()
        form.setSpacing(11)
        self.name_input = QLineEdit()
        self.presentation_input = QLineEdit()
        self.supplier_combo = QComboBox()
        for supplier_id, name in self._service.list_suppliers():
            self.supplier_combo.addItem(name, supplier_id)
        self.category_combo = QComboBox()
        for category_id, name in self._service.list_categories():
            self.category_combo.addItem(name, category_id)
        self.price_input = QSpinBox()
        self.price_input.setRange(0, 99_999_999)
        self.price_input.setPrefix("$ ")
        self.price_input.setSpecialValueText("Sin precio")
        self.price_input.setGroupSeparatorShown(True)
        form.addRow("Producto *", self.name_input)
        form.addRow("Presentación *", self.presentation_input)
        form.addRow("Proveedor", self.supplier_combo)
        form.addRow("Categoría", self.category_combo)
        form.addRow("Precio mayorista", self.price_input)
        buttons = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        save = button("Guardar", "save", "PrimaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(form)
        layout.addLayout(buttons)
        if product:
            self.name_input.setText(product.name)
            self.presentation_input.setText(product.presentation)
            self.price_input.setValue(int(product.wholesale_price or 0))
            self.supplier_combo.setCurrentIndex(self.supplier_combo.findData(product.supplier_id))
            self.category_combo.setCurrentIndex(self.category_combo.findData(product.category_id))

    def _save(self) -> None:
        try:
            price = Decimal(self.price_input.value()) if self.price_input.value() else None
            values = {
                "name": self.name_input.text(),
                "presentation": self.presentation_input.text(),
                "supplier_id": int(self.supplier_combo.currentData()),
                "category_id": int(self.category_combo.currentData()),
                "wholesale_price": price,
            }
            if self._product:
                self._service.update_product(self._product.id, **values)
            else:
                self._service.create_product(**values)
        except ValueError as error:
            QMessageBox.warning(self, "Revisa los datos", str(error))
            return
        self.accept()


class ProductHistoryDialog(QDialog):
    def __init__(self, service: ProductService, product: ProductSummary, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Historial de precio · {product.name}")
        self.resize(720, 430)
        layout = QVBoxLayout(self)
        title = QLabel(f"{product.name} · {product.presentation}")
        title.setObjectName("PanelTitle")
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Fecha", "Precio anterior", "Precio nuevo", "Motivo"])
        configure_table(table, 3)
        rows = service.price_history(product.id)
        table.setRowCount(len(rows))
        for row, change in enumerate(rows):
            values = [
                change.changed_at.strftime("%d/%m/%Y %H:%M"),
                format_money(change.old_price),
                format_money(change.new_price),
                change.reason,
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        close = QPushButton("Cerrar")
        close.clicked.connect(self.accept)
        layout.addWidget(title)
        layout.addWidget(table, 1)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
