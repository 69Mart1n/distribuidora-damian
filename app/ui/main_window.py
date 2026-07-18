from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.engine import Engine

from app.config import AppConfig
from app.services.database_status_service import DatabaseStatusService
from app.ui.common import LOGO_DIR, button, icon
from app.ui.pages.backups_page import BackupsPage
from app.ui.pages.customers_page import CustomersPage
from app.ui.pages.export_page import ExportPage
from app.ui.pages.import_page import ImportPage
from app.ui.pages.new_receipt_page import NewReceiptPage
from app.ui.pages.price_update_page import PriceUpdatePage
from app.ui.pages.products_page import ProductsPage
from app.ui.pages.receipt_history_page import ReceiptHistoryPage
from app.ui.pages.settings_page import SettingsPage

NAVIGATION = [
    ("Inicio", "house"),
    ("Nueva boleta", "file-plus-2"),
    ("Productos", "package-search"),
    ("Clientes", "users"),
    ("Historial", "history"),
    ("Precios", "badge-dollar-sign"),
    ("Importar", "file-input"),
    ("Exportar", "file-output"),
    ("Respaldos", "database-backup"),
    ("Configuración", "settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, engine: Engine) -> None:
        super().__init__()
        self._config = config
        self._engine = engine
        self._nav_buttons: dict[str, QPushButton] = {}
        self.setWindowTitle("Distribuidora Damián")
        self.setMinimumSize(800, 500)
        self.resize(1366, 820)
        self._build_shell()
        self._show_page("Inicio")

    def _build_shell(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.stack = QStackedWidget()
        self.home_page = self._build_home_page()
        self.receipt_page = NewReceiptPage(self._engine, self._config.exports_dir)
        self.products_page = ProductsPage(self._engine)
        self.customers_page = CustomersPage(self._engine)
        self.history_page = ReceiptHistoryPage(self._engine, self._config.exports_dir)
        self.price_page = PriceUpdatePage(
            self._engine, self._config.database_path, self._config.backups_dir
        )
        self.import_page = ImportPage(
            self._engine,
            self._config.imports_dir,
            self._config.database_path,
            self._config.backups_dir,
        )
        self.export_page = ExportPage(self._engine, self._config.exports_dir)
        self.backups_page = BackupsPage(self._config.database_path, self._config.backups_dir)
        self.settings_page = SettingsPage(
            self._engine, self._config.exports_dir, self._config.backups_dir
        )
        self._pages = {
            "Inicio": self._wrap_page(self.home_page),
            "Nueva boleta": self._wrap_page(self.receipt_page),
            "Productos": self._wrap_page(self.products_page),
            "Clientes": self._wrap_page(self.customers_page),
            "Historial": self._wrap_page(self.history_page),
            "Precios": self._wrap_page(self.price_page),
            "Importar": self._wrap_page(self.import_page),
            "Exportar": self._wrap_page(self.export_page),
            "Respaldos": self._wrap_page(self.backups_page),
            "Configuración": self._wrap_page(self.settings_page),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)
        self.history_page.edit_requested.connect(self._edit_receipt)
        self.history_page.duplicate_requested.connect(self._duplicate_receipt)
        self.customers_page.create_receipt_requested.connect(self._receipt_for_customer)
        self.receipt_page.receipt_saved.connect(lambda _receipt_id: self.history_page.refresh())
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    @staticmethod
    def _wrap_page(page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(4)
        logo = QLabel()
        logo_path = LOGO_DIR / "distribuidora_simbolo.png"
        pixmap = QPixmap(str(logo_path))
        logo.setPixmap(
            pixmap.scaled(
                64,
                52,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        logo.setFixedHeight(54)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("DISTRIBUIDORA DAMIÁN")
        brand.setStyleSheet("color: white; font-size: 15px; font-weight: 700;")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline = QLabel("Gestión comercial")
        tagline.setObjectName("SidebarSubtitle")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addWidget(brand)
        layout.addWidget(tagline)
        layout.addSpacing(12)
        for name, icon_name in NAVIGATION:
            nav = QPushButton(name)
            nav.setObjectName("NavButton")
            nav.setCheckable(True)
            nav.setProperty("iconName", icon_name)
            nav.setIcon(icon(icon_name, light=True))
            nav.setIconSize(nav.iconSize().expandedTo(nav.iconSize()))
            nav.clicked.connect(lambda _checked=False, page=name: self._show_page(page))
            self._nav_buttons[name] = nav
            layout.addWidget(nav)
        layout.addStretch(1)
        return sidebar

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(15)
        title = QLabel("Distribuidora Damián")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Panel comercial")
        subtitle.setObjectName("PageDescription")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        primary = button("Nueva boleta\nRegistrar una venta", "file-plus-2", "HomePrimary")
        primary.clicked.connect(lambda: self._show_page("Nueva boleta"))
        layout.addWidget(primary)
        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.metric_products = self._metric_card("Productos", "0")
        self.metric_receipts = self._metric_card("Boletas", "0")
        self.metric_suppliers = self._metric_card("Proveedores", "0")
        self.metric_categories = self._metric_card("Categorías", "0")
        for index, card in enumerate(
            [
                self.metric_products,
                self.metric_receipts,
                self.metric_suppliers,
                self.metric_categories,
            ]
        ):
            metrics.addWidget(card, 0, index)
        layout.addLayout(metrics)
        section = QLabel("Accesos rápidos")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)
        actions = QGridLayout()
        actions.setSpacing(10)
        quick = [
            ("Productos", "package-search"),
            ("Clientes", "users"),
            ("Historial", "history"),
            ("Precios", "badge-dollar-sign"),
            ("Importar", "file-input"),
            ("Respaldos", "database-backup"),
        ]
        for index, (name, icon_name) in enumerate(quick):
            action = button(name, icon_name, "HomeAction")
            action.clicked.connect(
                lambda _checked=False, page_name=name: self._show_page(page_name)
            )
            actions.addWidget(action, index // 3, index % 3)
        layout.addLayout(actions)
        layout.addStretch(1)
        return page

    @staticmethod
    def _metric_card(label: str, initial: str) -> QFrame:
        card = QFrame()
        card.setObjectName("MetricCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 12, 16, 12)
        value = QLabel(initial)
        value.setObjectName("MetricValue")
        caption = QLabel(label)
        caption.setObjectName("MetricCaption")
        box.addWidget(value)
        box.addWidget(caption)
        return card

    def _show_page(self, name: str) -> None:
        page = self._pages[name]
        if name == "Inicio":
            self._refresh_dashboard()
        elif name == "Nueva boleta":
            self.receipt_page.refresh_data()
        elif name == "Productos":
            self.products_page.refresh()
        elif name == "Clientes":
            self.customers_page.refresh()
        elif name == "Historial":
            self.history_page.refresh()
        elif name == "Respaldos":
            self.backups_page.refresh()
        elif name == "Configuración":
            self.settings_page.refresh()
        self.stack.setCurrentWidget(page)
        for button_name, nav in self._nav_buttons.items():
            checked = button_name == name
            nav.setChecked(checked)
            nav.setIcon(icon(str(nav.property("iconName")), light=not checked))

    def _refresh_dashboard(self) -> None:
        status = DatabaseStatusService(self._engine, self._config.database_path).get_status()
        values = [
            (self.metric_products, status.products_count),
            (self.metric_receipts, status.receipts_count),
            (self.metric_suppliers, status.suppliers_count),
            (self.metric_categories, status.categories_count),
        ]
        for card, value in values:
            label = card.findChild(QLabel, "MetricValue")
            if label:
                label.setText(f"{value:,}".replace(",", "."))

    def _edit_receipt(self, receipt_id: int) -> None:
        self.receipt_page.refresh_data()
        self.receipt_page.load_receipt(receipt_id)
        self._show_page("Nueva boleta")

    def _duplicate_receipt(self, receipt_id: int) -> None:
        self.receipt_page.refresh_data()
        self.receipt_page.load_duplicate(receipt_id)
        self._show_page("Nueva boleta")

    def _receipt_for_customer(self, customer_id: int) -> None:
        self.receipt_page.start_for_customer(customer_id)
        self._show_page("Nueva boleta")
