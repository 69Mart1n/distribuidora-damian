from __future__ import annotations

import hashlib
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

from msilib import (  # noqa: E402
    Binary,
    CAB,
    Directory,
    Feature,
    add_data,
    add_tables,
    init_database,
    schema,
    sequence,
)

PRODUCT_NAME = "Distribuidora Damian"
PRODUCT_VERSION = "1.0.0"
MANUFACTURER = "Distribuidora Damian"
PRODUCT_CODE = "{33BE3E52-0C88-4FF9-B5DB-E501AD055674}"
UPGRADE_CODE = "{A56F96B2-7D16-4C73-9016-838625631A41}"


def _msi_id(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.]", "_", value)
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    available = 70 - len(prefix) - len(digest) - 2
    return f"{prefix}_{cleaned[:available]}_{digest}"


def build_msi(project_dir: Path) -> Path:
    payload_dir = project_dir / "release" / "payload"
    output_path = project_dir / "release" / "Instalador_Distribuidora_Damian.msi"
    marker = payload_dir / "runtime" / "distribuidora-runtime.marker"
    icon_path = payload_dir / "app" / "assets" / "icons" / "distribuidora_damian.ico"

    if not marker.exists() or not icon_path.exists():
        raise RuntimeError("El payload no esta preparado. Ejecuta build_installer.ps1 primero.")

    database = init_database(
        str(output_path),
        schema,
        PRODUCT_NAME,
        PRODUCT_CODE,
        PRODUCT_VERSION,
        MANUFACTURER,
    )
    add_tables(database, sequence)
    add_data(
        database,
        "Property",
        [
            ("UpgradeCode", UPGRADE_CODE),
            ("MSIINSTALLPERUSER", "1"),
            ("LIMITUI", "1"),
            ("ARPNOMODIFY", "1"),
            ("ARPNOREPAIR", "1"),
            ("ARPPRODUCTICON", "DistribuidoraIcon"),
        ],
    )
    add_data(
        database,
        "Icon",
        [("DistribuidoraIcon", Binary(str(icon_path)))],
    )

    cabinet = CAB("distribuidora.cab")
    feature = Feature(
        database,
        "MainFeature",
        PRODUCT_NAME,
        "Sistema comercial completo",
        1,
        directory="INSTALLDIR",
    )
    feature.set_current()

    target = Directory(
        database,
        cabinet,
        None,
        str(payload_dir),
        "TARGETDIR",
        "SourceDir",
        componentflags=0,
    )
    local_app_data = Directory(
        database,
        cabinet,
        target,
        ".",
        "LocalAppDataFolder",
        ".",
        componentflags=0,
    )
    programs = Directory(
        database,
        cabinet,
        local_app_data,
        ".",
        "ProgramsFolder",
        "Programs",
        componentflags=0,
    )
    install_dir = Directory(
        database,
        cabinet,
        programs,
        ".",
        "INSTALLDIR",
        "DISTRI~1|Distribuidora Damian",
        componentflags=0,
    )
    desktop = Directory(
        database,
        cabinet,
        target,
        ".",
        "DesktopFolder",
        ".",
        componentflags=0,
    )
    start_menu = Directory(
        database,
        cabinet,
        target,
        ".",
        "ProgramMenuFolder",
        ".",
        componentflags=0,
    )

    directory_counter = 0
    pythonw_file_id: str | None = None
    pythonw_component: str | None = None
    app_directory_id: str | None = None

    def add_tree(parent: Directory, physical_dir: Path, relative_dir: Path) -> None:
        nonlocal directory_counter, pythonw_file_id, pythonw_component, app_directory_id

        component_id = _msi_id("Component", str(relative_dir) or "Root")
        parent.start_component(component=component_id, feature=feature, flags=0)
        if relative_dir.as_posix() == "app":
            app_directory_id = parent.logical

        for file_path in sorted(
            (path for path in physical_dir.iterdir() if path.is_file()),
            key=lambda path: path.name.lower(),
        ):
            file_id = parent.add_file(file_path.name)
            if relative_dir.as_posix() == "runtime" and file_path.name.lower() == "pythonw.exe":
                pythonw_file_id = file_id
                pythonw_component = parent.component

        for child_path in sorted(
            (path for path in physical_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name.lower(),
        ):
            directory_counter += 1
            relative_child = relative_dir / child_path.name
            child_directory = Directory(
                database,
                cabinet,
                parent,
                child_path.name,
                _msi_id("Directory", str(relative_child)),
                f"D{directory_counter:07X}|{child_path.name}",
                componentflags=0,
            )
            add_tree(child_directory, child_path, relative_child)

    add_tree(install_dir, payload_dir, Path())

    if pythonw_file_id is None or pythonw_component is None or app_directory_id is None:
        raise RuntimeError("No se encontraron los archivos principales para crear accesos directos.")

    shortcut_name = "DISTRI~1|Distribuidora Damian"
    shortcut_arguments = f'"[{app_directory_id}]main.py"'
    add_data(
        database,
        "Shortcut",
        [
            (
                "DesktopShortcut",
                desktop.logical,
                shortcut_name,
                pythonw_component,
                f"[#{pythonw_file_id}]",
                shortcut_arguments,
                "Abrir Distribuidora Damian",
                None,
                "DistribuidoraIcon",
                0,
                1,
                app_directory_id,
            ),
            (
                "StartMenuShortcut",
                start_menu.logical,
                shortcut_name,
                pythonw_component,
                f"[#{pythonw_file_id}]",
                shortcut_arguments,
                "Abrir Distribuidora Damian",
                None,
                "DistribuidoraIcon",
                0,
                1,
                app_directory_id,
            ),
        ],
    )

    cabinet.commit(database)
    database.Commit()
    return output_path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    try:
        result = build_msi(root)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(result)
