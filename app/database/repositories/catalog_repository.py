from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Category, Product, Receipt, Supplier


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_suppliers(self) -> int:
        return self._session.scalar(select(func.count(Supplier.id))) or 0

    def count_categories(self) -> int:
        return self._session.scalar(select(func.count(Category.id))) or 0

    def count_products(self) -> int:
        return self._session.scalar(select(func.count(Product.id))) or 0

    def count_receipts(self) -> int:
        return self._session.scalar(select(func.count(Receipt.id))) or 0

    def supplier_names(self) -> list[str]:
        return list(
            self._session.scalars(select(Supplier.name).order_by(Supplier.name.asc())).all()
        )

    def category_names(self) -> list[str]:
        return list(
            self._session.scalars(select(Category.name).order_by(Category.name.asc())).all()
        )
