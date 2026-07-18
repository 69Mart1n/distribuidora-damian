from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
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

from app.services.export_service import ExportService
from app.services.receipt_service import ReceiptService, ReceiptSummary
from app.services.share_service import ShareService
from app.ui.common import button, configure_table, page_header, search_field
from app.ui.dialogs.receipt_preview_dialog import ReceiptPreviewDialog
from app.utils.money import format_money

PAYMENT_LABELS = {"paid": "Pagada", "partial": "Parcial", "pending": "Pendiente"}
METHOD_LABELS = {
    "cash": "Efectivo",
    "transfer": "Transferencia",
    "account": "Cuenta",
    "mixed": "Mixto",
}


class ReceiptHistoryPage(QWidget):
    edit_requested = Signal(int)
    duplicate_requested = Signal(int)

    def __init__(self, engine: Engine, exports_dir: Path) -> None:
        super().__init__()
        self._receipt_service = ReceiptService(engine)
        self._export_service = ExportService(engine, exports_dir)
        self._receipts: list[ReceiptSummary] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Historial de boletas",
                "Visualiza, imprime, edita, duplica, cancela o registra pagos posteriores.",
            )
        )
        filters = QHBoxLayout()
        self.search_input = search_field("Número, cliente o teléfono")
        self.search_input.textChanged.connect(self.refresh)
        self.payment_filter = QComboBox()
        self.payment_filter.addItem("Todos los pagos", None)
        self.payment_filter.addItem("Pagadas", "paid")
        self.payment_filter.addItem("Parciales", "partial")
        self.payment_filter.addItem("Pendientes", "pending")
        self.payment_filter.currentIndexChanged.connect(self.refresh)
        self.status_filter = QComboBox()
        self.status_filter.addItem("Todas", None)
        self.status_filter.addItem("Activas", "active")
        self.status_filter.addItem("Canceladas", "cancelled")
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.search_input, 1)
        filters.addWidget(self.payment_filter)
        filters.addWidget(self.status_filter)
        actions = QHBoxLayout()
        view_action = button("Ver e imprimir", "eye", "PrimaryButton")
        view_action.clicked.connect(self._preview)
        edit_action = button("Editar", "pencil")
        edit_action.clicked.connect(self._edit)
        duplicate_action = button("Duplicar", "copy")
        duplicate_action.clicked.connect(self._duplicate)
        pay_action = button("Registrar pago", "badge-dollar-sign", "AccentButton")
        pay_action.clicked.connect(self._register_payment)
        revisions_action = button("Revisiones", "history")
        revisions_action.clicked.connect(self._revisions)
        whatsapp_action = button("WhatsApp", "message-circle")
        whatsapp_action.clicked.connect(self._whatsapp)
        cancel_action = button("Cancelar boleta", "ban", "DangerButton")
        cancel_action.clicked.connect(self._cancel)
        for action in [
            view_action,
            edit_action,
            duplicate_action,
            pay_action,
            revisions_action,
            whatsapp_action,
            cancel_action,
        ]:
            actions.addWidget(action)
        actions.addStretch(1)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Boleta", "Fecha", "Cliente", "Total", "Abonado", "Saldo", "Pago", "Estado"]
        )
        configure_table(self.table, 2)
        self.table.doubleClicked.connect(self._preview)
        layout.addLayout(filters)
        layout.addLayout(actions)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        self._receipts = self._receipt_service.list_receipts(
            self.search_input.text(),
            payment_status=self.payment_filter.currentData(),
            status=self.status_filter.currentData(),
        )
        self.table.setRowCount(len(self._receipts))
        for row, receipt in enumerate(self._receipts):
            values = [
                receipt.receipt_code,
                receipt.issued_at.strftime("%d/%m/%Y %H:%M"),
                receipt.customer_name,
                format_money(receipt.total),
                format_money(receipt.amount_paid),
                format_money(receipt.pending_amount),
                PAYMENT_LABELS.get(receipt.payment_status, receipt.payment_status),
                "Activa" if receipt.status == "active" else "Cancelada",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, receipt.id)
                if column in {3, 4, 5}:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)

    def _selected(self) -> ReceiptSummary | None:
        row = self.table.currentRow()
        return self._receipts[row] if 0 <= row < len(self._receipts) else None

    def _require_selected(self) -> ReceiptSummary | None:
        selected = self._selected()
        if selected is None:
            QMessageBox.warning(self, "Selección requerida", "Selecciona una boleta.")
        return selected

    def _preview(self) -> None:
        selected = self._require_selected()
        if selected:
            ReceiptPreviewDialog(self._export_service.export_receipt_pdf(selected.id), self).exec()

    def _edit(self) -> None:
        selected = self._require_selected()
        if selected and selected.status == "active":
            self.edit_requested.emit(selected.id)
        elif selected:
            QMessageBox.warning(
                self, "Boleta cancelada", "No se puede editar una boleta cancelada."
            )

    def _duplicate(self) -> None:
        selected = self._require_selected()
        if selected:
            self.duplicate_requested.emit(selected.id)

    def _register_payment(self) -> None:
        selected = self._require_selected()
        if selected is None:
            return
        if selected.status != "active" or selected.pending_amount <= 0:
            QMessageBox.information(self, "Sin saldo", "La boleta no tiene saldo pendiente activo.")
            return
        dialog = PaymentDialog(int(selected.pending_amount), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._receipt_service.register_payment(
                selected.id, dialog.method(), Decimal(dialog.amount()), dialog.notes()
            )
        except ValueError as error:
            QMessageBox.warning(self, "No se pudo registrar", str(error))
            return
        self.refresh()
        self._preview()

    def _cancel(self) -> None:
        selected = self._require_selected()
        if selected is None:
            return
        reason, accepted = QInputDialog.getText(
            self, "Cancelar boleta", "Motivo obligatorio de la cancelación:"
        )
        if not accepted:
            return
        try:
            self._receipt_service.cancel_receipt(selected.id, reason)
        except ValueError as error:
            QMessageBox.warning(self, "No se pudo cancelar", str(error))
            return
        self.refresh()

    def _revisions(self) -> None:
        selected = self._require_selected()
        if selected:
            RevisionsDialog(self._receipt_service, selected.id, self).exec()

    def _whatsapp(self) -> None:
        selected = self._require_selected()
        if selected is None:
            return
        path = self._export_service.export_receipt_pdf(selected.id)
        result = ShareService.share_whatsapp(path, selected.receipt_code, selected.customer_phone)
        QMessageBox.information(self, "Compartir boleta", result)


class PaymentDialog(QDialog):
    def __init__(self, pending: int, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registrar pago")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItem("Efectivo", "cash")
        self.method_combo.addItem("Transferencia", "transfer")
        self.amount_input = QSpinBox()
        self.amount_input.setRange(1, pending)
        self.amount_input.setValue(pending)
        self.amount_input.setPrefix("$ ")
        self.notes_input = QLineEdit()
        form.addRow("Medio", self.method_combo)
        form.addRow("Importe", self.amount_input)
        form.addRow("Nota", self.notes_input)
        actions = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        save = button("Registrar", "save", "PrimaryButton")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        actions.addStretch(1)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(form)
        layout.addLayout(actions)

    def method(self) -> str:
        return str(self.method_combo.currentData())

    def amount(self) -> int:
        return self.amount_input.value()

    def notes(self) -> str:
        return self.notes_input.text()


class RevisionsDialog(QDialog):
    def __init__(self, service: ReceiptService, receipt_id: int, parent: QWidget) -> None:
        super().__init__(parent)
        receipt = service.get_receipt(receipt_id)
        self.setWindowTitle(f"Revisiones · {receipt.receipt_code}")
        self.resize(760, 430)
        layout = QVBoxLayout(self)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["Revisión", "Fecha", "Motivo", "Cliente", "Total", "Estado de pago"]
        )
        configure_table(table, 2)
        revisions = sorted(receipt.revisions, key=lambda row: row.revision_number, reverse=True)
        table.setRowCount(len(revisions))
        for row, revision in enumerate(revisions):
            values = [
                str(revision.revision_number),
                revision.created_at.strftime("%d/%m/%Y %H:%M"),
                revision.reason,
                revision.customer_name_snapshot,
                format_money(revision.total),
                PAYMENT_LABELS.get(revision.payment_status, revision.payment_status),
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        close = QPushButton("Cerrar")
        close.clicked.connect(self.accept)
        layout.addWidget(table, 1)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
