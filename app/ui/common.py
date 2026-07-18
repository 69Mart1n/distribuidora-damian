from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
LOGO_DIR = ASSETS_DIR / "logo"


def icon(name: str, *, light: bool = False) -> QIcon:
    directory = ICONS_DIR / "white" if light else ICONS_DIR
    return QIcon(str(directory / f"{name}.svg"))


def button(text: str, icon_name: str | None = None, style: str = "SecondaryButton") -> QPushButton:
    result = QPushButton(text)
    result.setObjectName(style)
    if icon_name:
        result.setProperty("iconName", icon_name)
        result.setIcon(icon(icon_name, light=style in {"PrimaryButton", "HomePrimary"}))
        result.setIconSize(QSize(18, 18))
    return result


def page_header(title: str, description: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("PageHeader")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 4)
    layout.setSpacing(4)
    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    description_label = QLabel(description)
    description_label.setObjectName("PageDescription")
    description_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(description_label)
    return frame


def search_field(placeholder: str) -> QLineEdit:
    field = QLineEdit()
    field.setObjectName("SearchField")
    field.setPlaceholderText(placeholder)
    field.setClearButtonEnabled(True)
    field.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
    return field


def configure_table(table: QTableWidget, stretch_column: int = 1) -> None:
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(42)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)


def status_label(text: str, kind: str = "neutral") -> QLabel:
    label = QLabel(text)
    label.setObjectName("StatusLabel")
    label.setProperty("kind", kind)
    return label
