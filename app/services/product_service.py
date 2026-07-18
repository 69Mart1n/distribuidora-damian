from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.engine import Engine

from app.database.connection import build_session_factory, session_scope
from app.database.models import Category, PriceHistory, Product, Supplier
from app.utils.money import require_whole_number, to_money
from app.utils.text import normalize_text


@dataclass(frozen=True)
class ProductSummary:
    id: int
    code: str
    name: str
    presentation: str
    supplier_id: int
    supplier: str
    category_id: int
    category: str
    wholesale_price: Decimal | None
    requires_review: bool
    active: bool
    updated_at: datetime

    @property
    def display_name(self) -> str:
        return f"{self.name} - {self.presentation}"


@dataclass(frozen=True)
class PriceHistorySummary:
    old_price: Decimal | None
    new_price: Decimal | None
    reason: str
    source: str
    changed_at: datetime


class ProductService:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = build_session_factory(engine)

    def list_products(
        self,
        search: str = "",
        *,
        supplier_id: int | None = None,
        category_id: int | None = None,
        include_inactive: bool = False,
        only_without_price: bool = False,
    ) -> list[ProductSummary]:
        with session_scope(self._session_factory) as session:
            statement = (
                select(Product)
                .join(Product.supplier)
                .join(Product.category)
                .order_by(Product.name.asc(), Product.presentation.asc())
            )
            if not include_inactive:
                statement = statement.where(Product.active.is_(True))
            if supplier_id:
                statement = statement.where(Product.supplier_id == supplier_id)
            if category_id:
                statement = statement.where(Product.category_id == category_id)
            if only_without_price:
                statement = statement.where(Product.wholesale_price.is_(None))
            normalized = normalize_text(search)
            if normalized:
                like = f"%{normalized}%"
                statement = statement.where(
                    or_(
                        Product.normalized_name.like(like),
                        Product.presentation.like(f"%{search.strip()}%"),
                        Product.internal_code.like(f"%{search.strip()}%"),
                        Supplier.normalized_name.like(like),
                    )
                )
            return [self._summary(product) for product in session.scalars(statement).all()]

    def list_suppliers(self, *, include_inactive: bool = False) -> list[tuple[int, str]]:
        with session_scope(self._session_factory) as session:
            statement = select(Supplier.id, Supplier.name).order_by(Supplier.name)
            if not include_inactive:
                statement = statement.where(Supplier.active.is_(True))
            return [(row.id, row.name) for row in session.execute(statement).all()]

    def list_categories(self, *, include_inactive: bool = False) -> list[tuple[int, str]]:
        with session_scope(self._session_factory) as session:
            statement = select(Category.id, Category.name).order_by(Category.name)
            if not include_inactive:
                statement = statement.where(Category.active.is_(True))
            return [(row.id, row.name) for row in session.execute(statement).all()]

    def create_product(
        self,
        name: str,
        presentation: str,
        supplier_id: int,
        category_id: int,
        wholesale_price: Decimal | None,
    ) -> ProductSummary:
        clean_name, clean_presentation = self._validate_text(name, presentation)
        clean_price = self._validate_price(wholesale_price)
        with session_scope(self._session_factory) as session:
            supplier, category = self._validate_catalog(session, supplier_id, category_id)
            duplicate = session.scalar(
                select(Product).where(
                    Product.normalized_name == normalize_text(clean_name),
                    Product.presentation == clean_presentation,
                    Product.supplier_id == supplier_id,
                    Product.active.is_(True),
                )
            )
            if duplicate:
                raise ValueError("Ya existe un producto activo con esos datos.")
            last_id = session.scalar(select(Product.id).order_by(Product.id.desc()).limit(1)) or 0
            product = Product(
                internal_code=f"P{last_id + 1:04d}",
                name=clean_name,
                normalized_name=normalize_text(clean_name),
                presentation=clean_presentation,
                supplier_id=supplier.id,
                category_id=category.id,
                wholesale_price=to_money(clean_price) if clean_price is not None else None,
                requires_review=clean_price is None,
            )
            session.add(product)
            session.flush()
            return self._summary(product)

    def update_product(
        self,
        product_id: int,
        name: str,
        presentation: str,
        supplier_id: int,
        category_id: int,
        wholesale_price: Decimal | None,
    ) -> ProductSummary:
        clean_name, clean_presentation = self._validate_text(name, presentation)
        clean_price = self._validate_price(wholesale_price)
        with session_scope(self._session_factory) as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("El producto ya no está disponible.")
            supplier, category = self._validate_catalog(session, supplier_id, category_id)
            old_price = product.wholesale_price
            new_price = to_money(clean_price) if clean_price is not None else None
            product.name = clean_name
            product.normalized_name = normalize_text(clean_name)
            product.presentation = clean_presentation
            product.supplier_id = supplier.id
            product.category_id = category.id
            product.wholesale_price = new_price
            product.requires_review = new_price is None
            self._record_price_change(session, product, old_price, new_price, "Edición manual")
            session.flush()
            return self._summary(product)

    def duplicate_product(self, product_id: int) -> ProductSummary:
        with session_scope(self._session_factory) as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("No se encontró el producto.")
            last_id = session.scalar(select(Product.id).order_by(Product.id.desc()).limit(1)) or 0
            duplicate = Product(
                internal_code=f"P{last_id + 1:04d}",
                name=f"{product.name} copia",
                normalized_name=normalize_text(f"{product.name} copia"),
                presentation=product.presentation,
                supplier_id=product.supplier_id,
                category_id=product.category_id,
                wholesale_price=product.wholesale_price,
                requires_review=product.requires_review,
            )
            session.add(duplicate)
            session.flush()
            return self._summary(duplicate)

    def set_active(self, product_id: int, active: bool) -> None:
        with session_scope(self._session_factory) as session:
            product = session.get(Product, product_id)
            if product is None:
                raise ValueError("No se encontró el producto.")
            product.active = active

    def price_history(self, product_id: int) -> list[PriceHistorySummary]:
        with session_scope(self._session_factory) as session:
            rows = session.scalars(
                select(PriceHistory)
                .where(PriceHistory.product_id == product_id)
                .order_by(PriceHistory.changed_at.desc())
            ).all()
            return [
                PriceHistorySummary(
                    row.old_price,
                    row.new_price,
                    row.reason or "Sin detalle",
                    row.change_source,
                    row.changed_at,
                )
                for row in rows
            ]

    @staticmethod
    def _validate_price(value: Decimal | None) -> Decimal | None:
        return require_whole_number(value, "El precio") if value is not None else None

    @staticmethod
    def _validate_text(name: str, presentation: str) -> tuple[str, str]:
        clean_name = name.strip()
        clean_presentation = presentation.strip()
        if not clean_name:
            raise ValueError("Ingresa el nombre del producto.")
        if not clean_presentation:
            raise ValueError("Ingresa la presentación.")
        return clean_name, clean_presentation

    @staticmethod
    def _validate_catalog(session, supplier_id: int, category_id: int):  # type: ignore[no-untyped-def]
        supplier = session.get(Supplier, supplier_id)
        category = session.get(Category, category_id)
        if supplier is None or not supplier.active:
            raise ValueError("El proveedor seleccionado no es valido.")
        if category is None or not category.active:
            raise ValueError("La categoría seleccionada no es válida.")
        return supplier, category

    @staticmethod
    def _record_price_change(
        session,  # type: ignore[no-untyped-def]
        product: Product,
        old_price: Decimal | None,
        new_price: Decimal | None,
        reason: str,
    ) -> None:
        if old_price == new_price:
            return
        session.add(
            PriceHistory(
                product_id=product.id,
                price_type="wholesale",
                old_price=old_price,
                new_price=new_price,
                change_source="manual",
                reason=reason,
            )
        )

    @staticmethod
    def _summary(product: Product) -> ProductSummary:
        return ProductSummary(
            id=product.id,
            code=product.internal_code or "",
            name=product.name,
            presentation=product.presentation,
            supplier_id=product.supplier_id,
            supplier=product.supplier.name,
            category_id=product.category_id,
            category=product.category.name,
            wholesale_price=product.wholesale_price,
            requires_review=product.requires_review,
            active=product.active,
            updated_at=product.updated_at,
        )
