from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QPainter
from PySide6.QtPdf import QPdfDocument, QPdfDocumentRenderOptions
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class ReceiptPreviewDialog(QDialog):
    def __init__(self, pdf_path: Path, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self._pdf_path = pdf_path
        self.setWindowTitle(f"Vista previa - {pdf_path.stem}")
        self.resize(940, 760)
        self.setMinimumSize(720, 560)
        self._document = QPdfDocument(self)
        self._document.load(str(pdf_path))

        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        print_button = QPushButton("Imprimir")
        print_button.setObjectName("PrimaryButton")
        save_button = QPushButton("Guardar copia")
        close_button = QPushButton("Cerrar")
        print_button.clicked.connect(self._print)
        save_button.clicked.connect(self._save_copy)
        close_button.clicked.connect(self.accept)
        toolbar.addWidget(print_button)
        toolbar.addWidget(save_button)
        toolbar.addStretch(1)
        toolbar.addWidget(close_button)

        self.viewer = QPdfView()
        self.viewer.setDocument(self._document)
        self.viewer.setPageMode(QPdfView.PageMode.MultiPage)
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        layout.addLayout(toolbar)
        layout.addWidget(self.viewer, 1)

    def _save_copy(self) -> None:
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar copia de la boleta",
            self._pdf_path.name,
            "Documento PDF (*.pdf)",
        )
        if not destination:
            return
        if not destination.lower().endswith(".pdf"):
            destination += ".pdf"
        Path(destination).write_bytes(self._pdf_path.read_bytes())
        QMessageBox.information(self, "Copia guardada", f"Se guardo la boleta en:\n{destination}")

    def _print(self) -> None:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(self._pdf_path.stem)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        painter = QPainter(printer)
        if not painter.isActive():
            QMessageBox.warning(self, "No se pudo imprimir", "No se pudo iniciar la impresora.")
            return
        try:
            for page in range(self._document.pageCount()):
                if page:
                    printer.newPage()
                rect = printer.pageRect(QPrinter.Unit.DevicePixel)
                image = self._document.render(
                    page,
                    QSize(rect.width(), rect.height()),
                    QPdfDocumentRenderOptions(),
                )
                painter.drawImage(rect, image)
        finally:
            painter.end()
