from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication


class ShareService:
    @staticmethod
    def share_whatsapp(pdf_path: Path, receipt_code: str, customer_phone: str = "") -> str:
        message = f"Distribuidora Damián · Boleta {receipt_code}. Adjunto el comprobante en PDF."
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(message)

        # Windows ofrece este protocolo en versiones compatibles; el flujo alternativo
        # deja el chat y el archivo preparados cuando no está registrado.
        if QDesktopServices.openUrl(QUrl("ms-share:")):
            return "Se abrió el panel Compartir de Windows."

        phone = "".join(character for character in customer_phone if character.isdigit())
        target = (
            f"https://wa.me/{phone}?text={quote(message)}"
            if phone
            else (f"https://wa.me/?text={quote(message)}")
        )
        webbrowser.open(target)
        subprocess.Popen(["explorer.exe", "/select,", str(pdf_path.resolve())])
        return "Se abrió WhatsApp, se copió el mensaje y se seleccionó el PDF para adjuntarlo."
