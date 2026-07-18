from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.services.settings_service import SettingsService
from app.ui.common import LOGO_DIR, button, page_header


class SettingsPage(QWidget):
    def __init__(self, engine: Engine, exports_dir: Path, backups_dir: Path) -> None:
        super().__init__()
        self._service = SettingsService(engine)
        self._default_exports = exports_dir
        self._default_backups = backups_dir
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            page_header(
                "Configuración",
                "Datos comerciales, numeración, logo, rutas y política de respaldos.",
            )
        )
        tabs = QTabWidget()
        tabs.addTab(self._business_tab(), "Datos comerciales")
        tabs.addTab(self._documents_tab(), "Boletas")
        tabs.addTab(self._storage_tab(), "Archivos y respaldos")
        save = button("Guardar configuración", "save", "PrimaryButton")
        save.clicked.connect(self._save)
        layout.addWidget(tabs, 1)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)
        self.refresh()

    def _business_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        self.email_input = QLineEdit()
        self.logo_input = QLineEdit()
        browse = QPushButton("Elegir logo")
        browse.clicked.connect(self._choose_logo)
        logo_row = QHBoxLayout()
        logo_row.addWidget(self.logo_input, 1)
        logo_row.addWidget(browse)
        form.addRow("Nombre del negocio", self.name_input)
        form.addRow("Teléfono", self.phone_input)
        form.addRow("Dirección", self.address_input)
        form.addRow("Correo", self.email_input)
        form.addRow("Logo", logo_row)
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(260, 180)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(form, 1)
        layout.addWidget(self.logo_preview)
        return page

    def _documents_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.prefix_input = QLineEdit()
        self.prefix_input.setMaxLength(12)
        self.number_input = QSpinBox()
        self.number_input.setRange(500, 9_999_999)
        self.number_input.setGroupSeparatorShown(True)
        self.currency_input = QLineEdit("$")
        self.currency_input.setMaxLength(4)
        form.addRow("Prefijo de boleta", self.prefix_input)
        form.addRow("Próxima boleta", self.number_input)
        form.addRow("Moneda", self.currency_input)
        return page

    def _storage_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.exports_input = QLineEdit()
        self.backups_input = QLineEdit()
        self.backup_check = QCheckBox("Crear una copia automática diaria")
        self.retention_input = QSpinBox()
        self.retention_input.setRange(7, 365)
        self.monthly_input = QSpinBox()
        self.monthly_input.setRange(1, 60)
        form.addRow("Carpeta de exportaciones", self.exports_input)
        form.addRow("Carpeta de respaldos", self.backups_input)
        form.addRow("Respaldo automático", self.backup_check)
        form.addRow("Copias diarias", self.retention_input)
        form.addRow("Copias mensuales", self.monthly_input)
        return page

    def refresh(self) -> None:
        settings = self._service.get()
        self.name_input.setText(settings.business_name)
        self.phone_input.setText(settings.phone)
        self.address_input.setText(settings.address)
        self.email_input.setText(settings.email)
        self.prefix_input.setText(settings.receipt_prefix)
        self.number_input.setValue(settings.next_receipt_number)
        self.logo_input.setText(settings.logo_path or str(LOGO_DIR / "distribuidora_damian.png"))
        self.currency_input.setText(settings.currency_symbol)
        self.backup_check.setChecked(settings.backup_enabled)
        self.retention_input.setValue(settings.backup_retention_days)
        self.monthly_input.setValue(settings.monthly_retention_count)
        self.exports_input.setText(settings.exports_path or str(self._default_exports))
        self.backups_input.setText(settings.backups_path or str(self._default_backups))
        self._refresh_logo()

    def _choose_logo(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar logo", self.logo_input.text(), "Imágenes (*.png *.jpg *.jpeg)"
        )
        if selected:
            self.logo_input.setText(selected)
            self._refresh_logo()

    def _refresh_logo(self) -> None:
        pixmap = QPixmap(self.logo_input.text())
        self.logo_preview.setPixmap(
            pixmap.scaled(
                self.logo_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _save(self) -> None:
        try:
            self._service.save(
                self.name_input.text(),
                self.phone_input.text(),
                self.address_input.text(),
                self.email_input.text(),
                self.prefix_input.text(),
                self.number_input.value(),
                logo_path=self.logo_input.text(),
                currency_symbol=self.currency_input.text(),
                backup_enabled=self.backup_check.isChecked(),
                backup_retention_days=self.retention_input.value(),
                monthly_retention_count=self.monthly_input.value(),
                exports_path=self.exports_input.text(),
                backups_path=self.backups_input.text(),
            )
        except ValueError as error:
            QMessageBox.warning(self, "Revisa los datos", str(error))
            return
        QMessageBox.information(self, "Configuración guardada", "Los cambios fueron guardados.")
