from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.customer_service import CustomerService, CustomerSummary
from app.services.export_service import ExportService
from app.services.product_service import ProductService, ProductSummary
from app.services.receipt_service import PaymentInput, ReceiptLine, ReceiptService
from app.ui.common import button, configure_table, page_header, search_field
from app.ui.dialogs.receipt_preview_dialog import ReceiptPreviewDialog
from app.utils.money import format_money, to_money, to_pesos


@dataclass
class DraftLine:
    product: ProductSummary
    quantity: int
    unit_price: int

    @property
    def total(self) -> Decimal:
        return to_money(self.quantity * self.unit_price)


class NewReceiptPage(QWidget):
    receipt_saved = Signal(int)

    def __init__(self, engine: Engine, exports_dir: Path) -> None:
        super().__init__()
        self._engine = engine
        self._product_service = ProductService(engine)
        self._customer_service = CustomerService(engine)
        self._receipt_service = ReceiptService(engine)
        self._export_service = ExportService(engine, exports_dir)
        self._products: list[ProductSummary] = []
        self._visible_products: list[ProductSummary] = []
        self._customers: list[CustomerSummary] = []
        self._lines: list[DraftLine] = []
        self._editing_receipt_id: int | None = None
        self._saving = False
        self._build_ui()
        self.refresh_data()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Nueva boleta",
                "Selecciona el cliente, agrega productos y registra el estado del pago.",
            )
        )

        customer_panel = QFrame()
        customer_panel.setObjectName("Panel")
        customer_layout = QHBoxLayout(customer_panel)
        customer_layout.setContentsMargins(14, 11, 14, 11)
        customer_layout.addWidget(QLabel("Cliente"))
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer_combo.setMinimumWidth(320)
        self.customer_combo.lineEdit().setPlaceholderText("Cliente ocasional o buscar cliente")
        customer_layout.addWidget(self.customer_combo, 1)
        new_customer = button("Nuevo cliente", "plus")
        new_customer.clicked.connect(self._new_customer)
        customer_layout.addWidget(new_customer)
        self.editing_label = QLabel("")
        self.editing_label.setObjectName("StatusLabel")
        self.editing_label.setProperty("kind", "warning")
        self.editing_label.hide()
        customer_layout.addWidget(self.editing_label)
        layout.addWidget(customer_panel)

        work = QGridLayout()
        work.setHorizontalSpacing(13)
        catalog_panel = QFrame()
        catalog_panel.setObjectName("Panel")
        catalog_layout = QVBoxLayout(catalog_panel)
        catalog_layout.setContentsMargins(13, 13, 13, 13)
        catalog_layout.setSpacing(9)
        heading = QLabel("Buscar productos")
        heading.setObjectName("PanelTitle")
        self.search_input = search_field("Nombre, código, presentación o proveedor")
        self.search_input.textChanged.connect(self._filter_products)
        self.product_table = QTableWidget(0, 4)
        self.product_table.setHorizontalHeaderLabels(
            ["Producto", "Presentación", "Proveedor", "Precio"]
        )
        configure_table(self.product_table, 0)
        self.product_table.itemSelectionChanged.connect(self._sync_product)
        self.product_table.doubleClicked.connect(self._add_line)
        catalog_layout.addWidget(heading)
        catalog_layout.addWidget(self.search_input)
        catalog_layout.addWidget(self.product_table, 1)

        add_panel = QFrame()
        add_panel.setObjectName("Panel")
        add_layout = QVBoxLayout(add_panel)
        add_layout.setContentsMargins(14, 13, 14, 13)
        add_layout.setSpacing(8)
        add_title = QLabel("Agregar producto")
        add_title.setObjectName("PanelTitle")
        self.selected_label = QLabel("Selecciona un producto")
        self.selected_label.setWordWrap(True)
        self.selected_label.setMinimumHeight(44)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 9999)
        self.quantity_input.setValue(1)
        self.quantity_input.setSuffix(" unidades")
        self.price_input = QSpinBox()
        self.price_input.setRange(1, 99_999_999)
        self.price_input.setPrefix("$ ")
        self.price_input.setGroupSeparatorShown(True)
        add_action = button("Agregar", "plus", "PrimaryButton")
        add_action.clicked.connect(self._add_line)
        add_layout.addWidget(add_title)
        add_layout.addWidget(self.selected_label)
        add_layout.addWidget(QLabel("Cantidad entera"))
        add_layout.addWidget(self.quantity_input)
        add_layout.addWidget(QLabel("Precio por unidad"))
        add_layout.addWidget(self.price_input)
        add_layout.addStretch(1)
        add_layout.addWidget(add_action)
        work.addWidget(catalog_panel, 0, 0)
        work.addWidget(add_panel, 0, 1)
        work.setColumnStretch(0, 4)
        work.setColumnStretch(1, 1)
        layout.addLayout(work, 3)

        detail_bar = QHBoxLayout()
        detail_title = QLabel("Detalle de la boleta")
        detail_title.setObjectName("PanelTitle")
        remove = button("Quitar", "minus")
        remove.clicked.connect(self._remove_line)
        detail_bar.addWidget(detail_title)
        detail_bar.addStretch(1)
        detail_bar.addWidget(remove)
        layout.addLayout(detail_bar)
        self.lines_table = QTableWidget(0, 6)
        self.lines_table.setHorizontalHeaderLabels(
            ["Producto", "Presentación", "Cantidad", "Precio", "Subtotal", "Ajustar"]
        )
        configure_table(self.lines_table, 0)
        layout.addWidget(self.lines_table, 2)

        payment_panel = QFrame()
        payment_panel.setObjectName("Panel")
        payment_layout = QGridLayout(payment_panel)
        payment_layout.setContentsMargins(14, 11, 14, 11)
        payment_layout.setHorizontalSpacing(10)
        self.payment_status_combo = QComboBox()
        self.payment_status_combo.addItem("Pago completo", "paid")
        self.payment_status_combo.addItem("Pago parcial", "partial")
        self.payment_status_combo.addItem("Pendiente", "pending")
        self.payment_status_combo.currentIndexChanged.connect(self._sync_payment_controls)
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItem("Efectivo", "cash")
        self.payment_method_combo.addItem("Transferencia", "transfer")
        self.payment_method_combo.addItem("Cuenta", "account")
        self.payment_method_combo.addItem("Mixto", "mixed")
        self.payment_method_combo.currentIndexChanged.connect(self._sync_payment_controls)
        self.amount_paid_input = QSpinBox()
        self.amount_paid_input.setRange(0, 99_999_999)
        self.amount_paid_input.setPrefix("$ ")
        self.amount_paid_input.setGroupSeparatorShown(True)
        self.cash_input = QSpinBox()
        self.cash_input.setRange(0, 99_999_999)
        self.cash_input.setPrefix("Efectivo $ ")
        self.transfer_input = QSpinBox()
        self.transfer_input.setRange(0, 99_999_999)
        self.transfer_input.setPrefix("Transferencia $ ")
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Observaciones opcionales")
        self.notes_input.setMaximumHeight(64)
        payment_layout.addWidget(QLabel("Estado de pago"), 0, 0)
        payment_layout.addWidget(self.payment_status_combo, 1, 0)
        payment_layout.addWidget(QLabel("Medio de pago"), 0, 1)
        payment_layout.addWidget(self.payment_method_combo, 1, 1)
        payment_layout.addWidget(QLabel("Importe abonado"), 0, 2)
        payment_layout.addWidget(self.amount_paid_input, 1, 2)
        payment_layout.addWidget(self.cash_input, 1, 3)
        payment_layout.addWidget(self.transfer_input, 1, 4)
        payment_layout.addWidget(self.notes_input, 0, 5, 2, 1)
        payment_layout.setColumnStretch(5, 1)
        layout.addWidget(payment_panel)

        footer = QHBoxLayout()
        clear = button("Limpiar", "rotate-ccw")
        clear.clicked.connect(self.clear)
        self.total_label = QLabel("Total: $ 0")
        self.total_label.setObjectName("TotalLabel")
        self.save_button = button("Guardar y ver boleta", "save", "PrimaryButton")
        self.save_button.clicked.connect(self._save_receipt)
        footer.addWidget(clear)
        footer.addStretch(1)
        footer.addWidget(self.total_label)
        footer.addSpacing(18)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self._sync_payment_controls()

    def refresh_data(self) -> None:
        self.refresh_products()
        self._customers = self._customer_service.list_customers()
        current_id = self.customer_combo.currentData()
        current_text = self.customer_combo.currentText()
        self.customer_combo.clear()
        self.customer_combo.addItem("Cliente ocasional", None)
        for customer in self._customers:
            label = customer.name
            if customer.phone:
                label += f" · {customer.phone}"
            self.customer_combo.addItem(label, customer.id)
        index = self.customer_combo.findData(current_id)
        if index >= 0:
            self.customer_combo.setCurrentIndex(index)
        elif current_text and current_text != "Cliente ocasional":
            self.customer_combo.setEditText(current_text)

    def refresh_products(self) -> None:
        self._products = self._product_service.list_products()
        self._filter_products()

    def _filter_products(self) -> None:
        search = self.search_input.text().strip().casefold()
        self._visible_products = [
            product
            for product in self._products
            if product.wholesale_price is not None
            and (
                not search
                or search
                in " ".join(
                    [product.code, product.name, product.presentation, product.supplier]
                ).casefold()
            )
        ][:200]
        self.product_table.setRowCount(len(self._visible_products))
        for row, product in enumerate(self._visible_products):
            values = [
                product.name,
                product.presentation,
                product.supplier,
                format_money(product.wholesale_price),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 3:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.product_table.setItem(row, column, item)
        if self._visible_products:
            self.product_table.selectRow(0)
        else:
            self.selected_label.setText("No se encontraron productos con precio")

    def _current_product(self) -> ProductSummary | None:
        row = self.product_table.currentRow()
        return self._visible_products[row] if 0 <= row < len(self._visible_products) else None

    def _sync_product(self) -> None:
        product = self._current_product()
        if product is None:
            return
        self.selected_label.setText(f"{product.name}\n{product.presentation}")
        self.price_input.setValue(int(to_pesos(product.wholesale_price or 0)))

    def _add_line(self) -> None:
        product = self._current_product()
        if product is None:
            QMessageBox.warning(self, "Producto requerido", "Selecciona un producto con precio.")
            return
        quantity = self.quantity_input.value()
        price = self.price_input.value()
        existing = next((line for line in self._lines if line.product.id == product.id), None)
        if existing:
            existing.quantity += quantity
            existing.unit_price = price
        else:
            self._lines.append(DraftLine(product, quantity, price))
        self.quantity_input.setValue(1)
        self._refresh_lines()

    def _change_quantity(self, row: int, delta: int) -> None:
        if not 0 <= row < len(self._lines):
            return
        self._lines[row].quantity += delta
        if self._lines[row].quantity <= 0:
            self._lines.pop(row)
        self._refresh_lines()

    def _remove_line(self) -> None:
        row = self.lines_table.currentRow()
        if 0 <= row < len(self._lines):
            self._lines.pop(row)
            self._refresh_lines()

    def _refresh_lines(self) -> None:
        self.lines_table.setRowCount(len(self._lines))
        for row, line in enumerate(self._lines):
            values = [
                line.product.name,
                line.product.presentation,
                str(line.quantity),
                format_money(Decimal(line.unit_price)),
                format_money(line.total),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column >= 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.lines_table.setItem(row, column, item)
            controls = QWidget()
            control_layout = QHBoxLayout(controls)
            control_layout.setContentsMargins(2, 2, 2, 2)
            minus = button("", "minus", "IconButton")
            plus = button("", "plus", "IconButton")
            minus.setToolTip("Restar una unidad")
            plus.setToolTip("Sumar una unidad")
            minus.clicked.connect(
                lambda _checked=False, index=row: self._change_quantity(index, -1)
            )
            plus.clicked.connect(lambda _checked=False, index=row: self._change_quantity(index, 1))
            control_layout.addWidget(minus)
            control_layout.addWidget(plus)
            self.lines_table.setCellWidget(row, 5, controls)
        total = self._total()
        self.total_label.setText(f"Total: {format_money(total)}")
        self.amount_paid_input.setMaximum(int(total))
        self.cash_input.setMaximum(int(total))
        self.transfer_input.setMaximum(int(total))
        self._sync_payment_controls()

    def _total(self) -> Decimal:
        return sum((line.total for line in self._lines), Decimal("0"))

    def _sync_payment_controls(self) -> None:
        status = self.payment_status_combo.currentData()
        method = self.payment_method_combo.currentData()
        mixed = method == "mixed"
        self.cash_input.setVisible(mixed)
        self.transfer_input.setVisible(mixed)
        self.amount_paid_input.setVisible(not mixed)
        total = int(self._total())
        if status == "paid":
            if mixed:
                if self.cash_input.value() + self.transfer_input.value() != total:
                    self.cash_input.setValue(total)
                    self.transfer_input.setValue(0)
            else:
                self.amount_paid_input.setValue(total)
        elif status == "pending":
            self.amount_paid_input.setValue(0)
            self.cash_input.setValue(0)
            self.transfer_input.setValue(0)
        if method == "account" and status == "paid":
            self.payment_status_combo.setCurrentIndex(2)

    def _payments(self) -> tuple[list[PaymentInput], Decimal]:
        status = self.payment_status_combo.currentData()
        method = self.payment_method_combo.currentData()
        total = self._total()
        if status == "pending":
            return [], Decimal("0")
        if method == "mixed":
            payments = []
            if self.cash_input.value():
                payments.append(PaymentInput("cash", Decimal(self.cash_input.value())))
            if self.transfer_input.value():
                payments.append(PaymentInput("transfer", Decimal(self.transfer_input.value())))
            paid = sum((payment.amount for payment in payments), Decimal("0"))
        else:
            paid = Decimal(self.amount_paid_input.value())
            payments = [PaymentInput(method, paid)] if paid else []
        if status == "paid" and paid != total:
            raise ValueError("El pago completo debe coincidir con el total de la boleta.")
        if status == "partial" and (paid <= 0 or paid >= total):
            raise ValueError("El pago parcial debe ser mayor a cero y menor al total.")
        return payments, paid

    def _save_receipt(self) -> None:
        if self._saving:
            return
        self._saving = True
        self.save_button.setEnabled(False)
        try:
            payments, paid = self._payments()
            customer_id = self.customer_combo.currentData()
            customer_name = self.customer_combo.currentText().split(" · ", 1)[0]
            lines = [
                ReceiptLine(line.product.id, Decimal(line.quantity), Decimal(line.unit_price))
                for line in self._lines
            ]
            arguments = {
                "customer_id": customer_id,
                "payments": payments,
                "payment_method": self.payment_method_combo.currentData(),
                "amount_paid": paid,
                "notes": self.notes_input.toPlainText(),
            }
            if self._editing_receipt_id is not None:
                from PySide6.QtWidgets import QInputDialog

                reason, accepted = QInputDialog.getText(
                    self, "Motivo de edición", "Motivo obligatorio del cambio:"
                )
                if not accepted:
                    return
                created = self._receipt_service.update_receipt(
                    self._editing_receipt_id, reason, customer_name, lines, **arguments
                )
            else:
                created = self._receipt_service.create_receipt(customer_name, lines, **arguments)
            path = self._export_service.export_receipt_pdf(created.id)
            self.receipt_saved.emit(created.id)
            self.clear()
            ReceiptPreviewDialog(path, self).exec()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "No se pudo guardar", str(error))
        finally:
            self._saving = False
            self.save_button.setEnabled(True)

    def load_receipt(self, receipt_id: int) -> None:
        receipt = self._receipt_service.get_receipt(receipt_id)
        self.clear()
        self._editing_receipt_id = receipt.id
        self.editing_label.setText(f"Editando {receipt.receipt_code}")
        self.editing_label.show()
        self.save_button.setText("Guardar cambios y ver boleta")
        self._load_customer(receipt.customer_id, receipt.customer_name_snapshot)
        products = {product.id: product for product in self._products}
        self._lines = [
            DraftLine(products[item.product_id], int(item.quantity), int(item.unit_price))
            for item in receipt.items
            if item.product_id in products
        ]
        self.notes_input.setPlainText(receipt.notes or "")
        self._set_payment(receipt.payment_status, receipt.payment_method, int(receipt.amount_paid))
        self._refresh_lines()

    def load_duplicate(self, receipt_id: int) -> None:
        data = self._receipt_service.duplicate_data(receipt_id)
        self.clear()
        self._load_customer(data.customer_id, data.customer_name)
        products = {product.id: product for product in self._products}
        self._lines = [
            DraftLine(products[line.product_id], int(line.quantity), int(line.unit_price))
            for line in data.lines
            if line.product_id in products
        ]
        self.notes_input.setPlainText(data.notes)
        self._refresh_lines()

    def start_for_customer(self, customer_id: int) -> None:
        self.clear()
        self.refresh_data()
        index = self.customer_combo.findData(customer_id)
        if index >= 0:
            self.customer_combo.setCurrentIndex(index)

    def _load_customer(self, customer_id: int | None, name: str) -> None:
        index = self.customer_combo.findData(customer_id)
        if index >= 0:
            self.customer_combo.setCurrentIndex(index)
        else:
            self.customer_combo.setEditText(name)

    def _set_payment(self, status: str, method: str, amount: int) -> None:
        status_index = self.payment_status_combo.findData(status)
        method_index = self.payment_method_combo.findData(method)
        self.payment_status_combo.setCurrentIndex(max(0, status_index))
        self.payment_method_combo.setCurrentIndex(max(0, method_index))
        self.amount_paid_input.setValue(amount)

    def _new_customer(self) -> None:
        from app.ui.pages.customers_page import CustomerDialog

        dialog = CustomerDialog(self._customer_service, self)
        if dialog.exec():
            self.refresh_data()
            if dialog.saved_customer_id:
                self.customer_combo.setCurrentIndex(
                    self.customer_combo.findData(dialog.saved_customer_id)
                )

    def clear(self) -> None:
        self._editing_receipt_id = None
        self._lines.clear()
        self.customer_combo.setCurrentIndex(0)
        self.notes_input.clear()
        self.payment_status_combo.setCurrentIndex(0)
        self.payment_method_combo.setCurrentIndex(0)
        self.amount_paid_input.setValue(0)
        self.cash_input.setValue(0)
        self.transfer_input.setValue(0)
        self.editing_label.hide()
        self.save_button.setText("Guardar y ver boleta")
        self._refresh_lines()
