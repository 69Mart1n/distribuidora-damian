from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine

from app.database.connection import build_session_factory, session_scope
from app.database.repositories.catalog_repository import CatalogRepository
from app.database.repositories.settings_repository import SettingsRepository


@dataclass(frozen=True)
class DatabaseStatus:
    business_name: str
    database_path: Path
    suppliers_count: int
    categories_count: int
    products_count: int
    receipts_count: int
    supplier_preview: tuple[str, ...]
    category_preview: tuple[str, ...]


class DatabaseStatusService:
    def __init__(self, engine: Engine, database_path: Path) -> None:
        self._session_factory = build_session_factory(engine)
        self._database_path = database_path

    def get_status(self) -> DatabaseStatus:
        with session_scope(self._session_factory) as session:
            settings = SettingsRepository(session).get_settings()
            catalog = CatalogRepository(session)
            return DatabaseStatus(
                business_name=settings.business_name,
                database_path=self._database_path,
                suppliers_count=catalog.count_suppliers(),
                categories_count=catalog.count_categories(),
                products_count=catalog.count_products(),
                receipts_count=catalog.count_receipts(),
                supplier_preview=tuple(catalog.supplier_names()[:6]),
                category_preview=tuple(catalog.category_names()[:6]),
            )
