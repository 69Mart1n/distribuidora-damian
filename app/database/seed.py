from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_CURRENCY_SYMBOL, DEFAULT_RECEIPT_PREFIX
from app.database.models import Category, Product, Settings, Supplier
from app.utils.text import normalize_text

SUPPLIER_NAMES = [
    "Matsuda",
    "Supra",
    "Districo",
    "Agrofeed",
    "Purina",
    "Negley",
    "Campera",
    "Nutrapet",
    "Nutrire",
    "Sadenir",
    "Kongo",
    "Matisse",
    "Pedigree",
    "CanFeed",
    "Vitalcan",
    "Grinor",
    "Otros",
]

CATEGORY_NAMES = [
    "Perros",
    "Gatos",
    "Aves",
    "Semillas",
    "Animales de granja",
    "Accesorios",
    "Antiparasitarios",
    "Snacks",
    "Otros",
]

SAMPLE_PRODUCTS = [
    ("Wits Perro", "8 kg", "Agrofeed", "Perros", "355"),
    ("Wits Perro", "25 kg", "Agrofeed", "Perros", "945"),
    ("Lager Perro", "10 kg", "Agrofeed", "Perros", "780"),
    ("Lager Gato", "22 kg", "Agrofeed", "Gatos", "1450"),
    ("Dog Chow Adulto", "21 kg", "Purina", "Perros", "2680"),
    ("Cat Chow Adulto", "15 kg", "Purina", "Gatos", "2350"),
    ("Maiz Entero", "Bolsa", "Otros", "Semillas", "620"),
    ("Alpiste", "1 kg", "Otros", "Semillas", "120"),
]


def seed_initial_data(session: Session) -> None:
    _seed_settings(session)
    _seed_suppliers(session)
    _seed_categories(session)
    session.flush()
    _seed_sample_products(session)


def _seed_settings(session: Session) -> None:
    exists = session.scalar(select(Settings).where(Settings.id == 1))
    if exists:
        return

    session.add(
        Settings(
            id=1,
            business_name="Distribuidora Damián",
            currency_symbol=DEFAULT_CURRENCY_SYMBOL,
            receipt_prefix=DEFAULT_RECEIPT_PREFIX,
            next_receipt_number=500,
            default_rounding="peso_entero",
            backup_enabled=True,
            backup_frequency="daily",
        )
    )


def _seed_suppliers(session: Session) -> None:
    existing = set(session.scalars(select(Supplier.normalized_name)).all())
    for name in SUPPLIER_NAMES:
        normalized = normalize_text(name)
        if normalized not in existing:
            session.add(Supplier(name=name, normalized_name=normalized))


def _seed_categories(session: Session) -> None:
    existing = set(session.scalars(select(Category.normalized_name)).all())
    for name in CATEGORY_NAMES:
        normalized = normalize_text(name)
        if normalized not in existing:
            session.add(Category(name=name, normalized_name=normalized))


def _seed_sample_products(session: Session) -> None:
    existing_products = session.scalar(select(Product.id).limit(1))
    if existing_products:
        return

    suppliers = {
        supplier.normalized_name: supplier for supplier in session.scalars(select(Supplier)).all()
    }
    categories = {
        category.normalized_name: category for category in session.scalars(select(Category)).all()
    }

    for index, (name, presentation, supplier_name, category_name, price) in enumerate(
        SAMPLE_PRODUCTS,
        start=1,
    ):
        supplier = suppliers[normalize_text(supplier_name)]
        category = categories[normalize_text(category_name)]
        session.add(
            Product(
                internal_code=f"P{index:04d}",
                name=name,
                normalized_name=normalize_text(name),
                supplier_id=supplier.id,
                category_id=category.id,
                presentation=presentation,
                wholesale_price=price,
                requires_review=False,
            )
        )
