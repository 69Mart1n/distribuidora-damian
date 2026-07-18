from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#F4F6F4"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#1B241F"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F7F9F7"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#1B241F"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1B241F"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#34533C"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    app.setStyleSheet(
        """
        * { font-family: "Segoe UI"; font-size: 14px; color: #1b241f; }
        QMainWindow, QStackedWidget, QWidget { background: #f4f6f4; }
        QLabel { background: transparent; }
        QLabel#PageTitle { font-size: 27px; font-weight: 700; color: #23392a; }
        QLabel#PageDescription { font-size: 14px; color: #68736c; }
        QLabel#PanelTitle, QLabel#SectionTitle {
            font-size: 17px; font-weight: 650; color: #23392a;
        }
        QLabel#TotalLabel { font-size: 24px; font-weight: 750; color: #294632; }
        QLabel#MetricValue { font-size: 25px; font-weight: 750; color: #34533c; }
        QLabel#MetricCaption { color: #68736c; font-size: 13px; }
        QLabel#StatusLabel { padding: 3px 8px; border-radius: 4px; font-weight: 600; }
        QLabel#StatusLabel[kind="success"] { background: #e6f2e9; color: #28613a; }
        QLabel#StatusLabel[kind="warning"] { background: #fff2d6; color: #795b16; }
        QLabel#StatusLabel[kind="danger"] { background: #fbe8e6; color: #913b32; }
        QFrame#Sidebar { background: #23392a; border: none; }
        QLabel#SidebarSubtitle { color: #bcc8bf; font-size: 12px; }
        QPushButton#NavButton {
            min-height: 21px; padding: 7px 10px; color: #eef3ef; background: transparent;
            border: none; border-radius: 5px; text-align: left; font-weight: 600;
        }
        QPushButton#NavButton:hover { background: #34533c; }
        QPushButton#NavButton:checked { background: #f3f0e7; color: #23392a; }
        QFrame#Panel, QFrame#MetricCard, QFrame#PrimaryAction {
            background: #ffffff; border: 1px solid #d8dfda; border-radius: 7px;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit {
            min-height: 23px; padding: 8px 10px; color: #1b241f; background: #ffffff;
            border: 1px solid #cbd4ce; border-radius: 5px; selection-background-color: #34533c;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QTextEdit:focus, QDateEdit:focus { border: 1px solid #496f53; }
        QComboBox QAbstractItemView { background: #ffffff; selection-background-color: #34533c; }
        QPushButton {
            min-height: 23px; padding: 8px 13px; background: #ffffff;
            border: 1px solid #cbd4ce; border-radius: 5px; font-weight: 600;
        }
        QPushButton:hover { border-color: #496f53; background: #f4f8f5; }
        QPushButton:disabled { color: #9aa39d; background: #edf0ee; border-color: #dce1dd; }
        QPushButton#PrimaryButton { color: #ffffff; background: #34533c; border-color: #34533c; }
        QPushButton#PrimaryButton:hover { background: #294632; }
        QPushButton#AccentButton { color: #23392a; background: #d7c18b; border-color: #c2a963; }
        QPushButton#DangerButton { color: #963b32; background: #ffffff; border-color: #d9a7a2; }
        QPushButton#IconButton { min-width: 33px; max-width: 33px; padding: 5px; }
        QPushButton#HomePrimary {
            min-height: 84px; padding: 18px; text-align: left; color: #ffffff;
            background: #34533c; border: 1px solid #34533c; font-size: 18px;
        }
        QPushButton#HomePrimary:hover { background: #294632; }
        QPushButton#HomeAction {
            min-height: 54px; padding: 12px 14px; text-align: left; background: #ffffff;
            border: 1px solid #d8dfda;
        }
        QTableWidget {
            color: #1b241f; background: #ffffff; alternate-background-color: #f7f9f7;
            gridline-color: #e4e9e5; border: 1px solid #d8dfda; border-radius: 5px;
            selection-background-color: #e4ece6; selection-color: #1b241f;
        }
        QTableWidget::item { color: #1b241f; padding: 5px; }
        QTableWidget::item:selected { color: #1b241f; background: #e4ece6; }
        QHeaderView::section {
            padding: 9px 7px; color: #3c4b42; background: #edf1ee; border: none;
            border-right: 1px solid #dce3de; border-bottom: 1px solid #d4ddd7; font-weight: 650;
        }
        QTabWidget::pane { border: 1px solid #d8dfda; background: #ffffff; }
        QTabBar::tab { padding: 9px 16px; background: #e9eeea; }
        QTabBar::tab:selected { background: #ffffff; color: #34533c; font-weight: 650; }
        QScrollBar:vertical { width: 12px; background: #eef1ef; }
        QScrollBar::handle:vertical { background: #aab6ae; min-height: 28px; border-radius: 4px; }
        QToolTip { color: #ffffff; background: #23392a; border: none; padding: 5px; }
        QMessageBox QLabel { color: #1b241f; }
        """
    )
