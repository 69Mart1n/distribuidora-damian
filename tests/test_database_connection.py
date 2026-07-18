from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, inspect, select, text

from app.database.connection import build_engine, initialize_database
from app.database.models import Category, PriceHistory, Receipt, ReceiptItem, Settings, Supplier
from app.database.seed import CATEGORY_NAMES, SUPPLIER_NAMES
from app.services.product_service import ProductService
from app.services.receipt_service import ReceiptLine, ReceiptService
from app.utils.text import normalize_text


def test_database_connection_responds(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"

    engine = initialize_database(database_url)

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_sqlite_foreign_keys_are_enabled(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = build_engine(database_url)

    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert foreign_keys == 1


def test_initial_schema_tables_are_created(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)

    table_names = set(inspect(engine).get_table_names())

    expected_tables = {
        "settings",
        "suppliers",
        "categories",
        "brands",
        "products",
        "price_history",
        "price_update_batches",
        "customers",
        "receipts",
        "receipt_items",
        "receipt_payments",
        "receipt_revisions",
        "receipt_revision_items",
        "imports",
        "import_rows",
        "exports",
        "backups",
        "schema_migrations",
    }
    assert expected_tables.issubset(table_names)


def test_initial_seed_is_inserted_once(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)
    initialize_database(database_url)

    with engine.connect() as connection:
        settings_count = connection.execute(select(func.count(Settings.id))).scalar_one()
        suppliers_count = connection.execute(select(func.count(Supplier.id))).scalar_one()
        categories_count = connection.execute(select(func.count(Category.id))).scalar_one()
        migration_count = connection.execute(
            text("SELECT count(*) FROM schema_migrations WHERE version = 1")
        ).scalar_one()

    assert settings_count == 1
    assert suppliers_count == len(SUPPLIER_NAMES)
    assert categories_count == len(CATEGORY_NAMES)
    assert migration_count == 1


def test_normalize_text_ignores_accents_case_and_extra_spaces() -> None:
    assert normalize_text("  Animales   de   Granja  ") == "animales de granja"
    assert normalize_text("Distribuidora Damián") == "distribuidora damian"


def test_seed_products_are_visible(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)

    products = ProductService(engine).list_products()

    assert len(products) >= 1
    assert any(product.name == "Wits Perro" for product in products)


def test_create_basic_receipt_persists_snapshot_and_total(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)
    product = ProductService(engine).list_products()[0]

    created = ReceiptService(engine).create_receipt(
        customer_name="Cliente de prueba",
        lines=[
            ReceiptLine(
                product_id=product.id,
                quantity=1,
                unit_price=product.wholesale_price,
            )
        ],
    )

    with engine.connect() as connection:
        receipts_count = connection.execute(select(func.count(Receipt.id))).scalar_one()
        items_count = connection.execute(select(func.count(ReceiptItem.id))).scalar_one()

    assert created.receipt_code == "BD-000500"
    assert created.total == product.wholesale_price
    assert receipts_count == 1
    assert items_count == 1


def test_receipt_rejects_fractional_quantity(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)
    product = ProductService(engine).list_products()[0]

    with pytest.raises(ValueError, match="entero"):
        ReceiptService(engine).create_receipt(
            customer_name="Cliente",
            lines=[
                ReceiptLine(
                    product_id=product.id,
                    quantity=Decimal("1.5"),
                    unit_price=product.wholesale_price,
                )
            ],
        )


def test_receipt_rejects_price_with_cents(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)
    product = ProductService(engine).list_products()[0]

    with pytest.raises(ValueError, match="entero"):
        ReceiptService(engine).create_receipt(
            customer_name="Cliente",
            lines=[
                ReceiptLine(
                    product_id=product.id,
                    quantity=1,
                    unit_price=Decimal("120.50"),
                )
            ],
        )


def test_product_price_edit_is_validated_and_recorded(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = initialize_database(database_url)
    service = ProductService(engine)
    product = service.list_products()[0]
    supplier_id = service.list_suppliers()[0][0]
    category_id = service.list_categories()[0][0]

    with pytest.raises(ValueError, match="entero"):
        service.update_product(
            product.id,
            product.name,
            product.presentation,
            supplier_id,
            category_id,
            Decimal("999.50"),
        )

    service.update_product(
        product.id,
        product.name,
        product.presentation,
        supplier_id,
        category_id,
        Decimal("999"),
    )
    with engine.connect() as connection:
        history_count = connection.execute(select(func.count(PriceHistory.id))).scalar_one()
    assert history_count == 1
