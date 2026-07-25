from __future__ import annotations

import ctypes
import os
import sys
import traceback
from pathlib import Path


def _report_startup_error(error: BaseException) -> None:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    log_dir = local_app_data / "Distribuidora Damian" / "logs"
    log_path = log_dir / "startup-error.log"
    details = "".join(traceback.format_exception(type(error), error, error.__traceback__))

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path.write_text(details, encoding="utf-8")
    except OSError:
        pass

    message = (
        "No se pudo iniciar Distribuidora Damian.\n\n"
        f"Detalle: {error}\n\n"
        f"Registro: {log_path}"
    )
    try:
        ctypes.windll.user32.MessageBoxW(0, message, "Distribuidora Damian", 0x10)
    except (AttributeError, OSError):
        print(message, file=sys.stderr)


if __name__ == "__main__":
    try:
        from app.application import run

        raise SystemExit(run(sys.argv))
    except SystemExit:
        raise
    except BaseException as error:
        _report_startup_error(error)
        raise SystemExit(1) from error
