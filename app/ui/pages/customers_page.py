from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.customer_service import CustomerService, CustomerSummary
from app.ui.common import button, configure_table, page_header, search_field
from app.utils.money import format_money


class CustomersPage(QWidget):
    create_receipt_requested = Signal(int)

    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self._service = CustomerService(engine)
        self._customers: list[CustomerSummary] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Clientes",
                "Consulta compras y saldos, edita los datos o inicia una nueva boleta.",
            )
        )
        toolbar = QHBoxLayout()
        self.search_input = search_field("Nombre, teléfono o documento")
        self.search_input.textChanged.connect(self.refresh)
        self.inactive_check = QCheckBox("Mostrar inactivos")
        self.inactive_check.toggled.connect(self.refresh)
        edit = button("Editar", "pencil")
        edit.clicked.connect(self._edit)
        self.toggle_button = button("Desactivar", "ban", "DangerButton")
        self.toggle_button.clicked.connect(self._toggle_active)
        create_receipt = button("Crear boleta", "file-plus-2", "AccentButton")
        create_receipt.clicked.connect(self._create_receipt)
        new = button("Nuevo cliente", "plus", "PrimaryButton")
        new.clicked.connect(self._new)
        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.inactive_check)
        toolbar.addWidget(edit)
        toolbar.addWidget(self.toggle_button)
        toolbar.addWidget(create_receipt)
        toolbar.addWidget(new)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            [
                "Nombre",
                "Teléfono",
                "Dirección",
                "Documento",
                "Boletas",
                "Total comprado",
                "Saldo",
                "Estado",
            ]
        )
        configure_table(self.table, 0)
        self.table.doubleClicked.connect(self._edit)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self._customers = self._service.list_customers(
            self.search_input.text(), include_inactive=self.inactive_check.isChecked()
        )
        self.table.setRowCount(len(self._customers))
        for row, customer in enumerate(self._customers):
            values = [
                customer.name,
                customer.phone or "-",
                customer.address or "-",
                customer.document or "-",
                str(customer.receipts_count),
                format_money(customer.total_purchased),
                format_money(customer.pending_balance),
                "Activo" if customer.active else "Inactivo",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {4, 5, 6}:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)
        self._selection_changed()

    def _selected(self) -> CustomerSummary | None:
        row = self.table.currentRow()
        return self._customers[row] if 0 <= row < len(self._customers) else None

    def _selection_changed(self) -> None:
        customer = self._selected()
        self.toggle_button.setText("Activar" if customer and not customer.active else "Desactivar")

    def _new(self) -> None:
        if CustomerDialog(self._service, self).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _edit(self) -> None:
        customer = self._selected()
        if customer is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un cliente.")
            return
        if CustomerDialog(self._service, self, customer).exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _toggle_active(self) -> None:
        customer = self._selected()
        if customer is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona un cliente.")
            return
        self._service.set_active(customer.id, not customer.active)
        self.refresh()

    def _create_receipt(self) -> None:
        customer = self._selected()
        if customer is None or not customer.active:
            QMessageBox.warning(self, "Cliente requerido", "Selecciona un cliente activo.")
            return
        self.create_receipt_requested.emit(customer.id)


class CustomerDialog(QDialog):
    def __init__(
        self,
        service: CustomerService,
        parent: QWidget,
        customer: CustomerSummary | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._customer = customer
        self.saved_customer_id: int | None = None
        self.setWindowTitle("Editar cliente" if customer else "Nuevo cliente")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(11)
        self.name_input = QLineEdit(customer.name if customer else "")
        self.phone_input = QLineEdit(customer.phone if customer else "")
        self.address_input = QLineEdit(customer.address if customer else "")
        self.document_input = QLineEdit(customer.document if customer else "")
        self.notes_input = QTextEdit(customer.notes if customer else "")
        self.notes_input.setMaximumHeight(90)
        form.addRow("Nombre *", self.name_input)
        form.addRow("Teléfono", self.phone_input)
        form.addRow("Dirección", self.address_input)
        form.addRow("Documento", self.document_input)
        form.addRow("Notas", self.notes_input)
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

    def _save(self) -> None:
        try:
            saved = self._service.save_customer(
                self._customer.id if self._customer else None,
                self.name_input.text(),
                self.phone_input.text(),
                self.address_input.text(),
                self.document_input.text(),
                self.notes_input.toPlainText(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Revisa los datos", str(error))
            return
        self.saved_customer_id = saved.id
        self.accept()
