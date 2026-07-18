from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.database.connection import initialize_database
from app.database.models import ReceiptPayment, ReceiptRevision
from app.services.backup_service import BackupService
from app.services.import_service import PriceListImportService
from app.services.price_service import PriceService
from app.services.product_service import ProductService
from app.services.receipt_service import PaymentInput, ReceiptLine, ReceiptService


@pytest.fixture
def services(tmp_path):  # type: ignore[no-untyped-def]
    database_path = tmp_path / "test.db"
    engine = initialize_database(f"sqlite:///{database_path.as_posix()}")
    return engine, database_path


def test_partial_payment_and_later_payment_are_auditable(services) -> None:  # type: ignore[no-untyped-def]
    engine, _ = services
    product = ProductService(engine).list_products()[0]
    total = product.wholesale_price
    initial = Decimal("100")
    created = ReceiptService(engine).create_receipt(
        "Cliente cuenta",
        [ReceiptLine(product.id, Decimal("1"), total)],
        payments=[PaymentInput("cash", initial)],
        amount_paid=initial,
    )

    assert created.payment_status == "partial"
    assert created.pending_amount == total - initial

    completed = ReceiptService(engine).register_payment(
        created.id, "transfer", created.pending_amount
    )
    assert completed.payment_status == "paid"
    assert completed.pending_amount == 0
    with engine.connect() as connection:
        assert connection.scalar(select(func.count(ReceiptPayment.id))) == 2
        assert connection.scalar(select(func.count(ReceiptRevision.id))) == 2


def test_receipt_edit_requires_reason_and_keeps_revision(services) -> None:  # type: ignore[no-untyped-def]
    engine, _ = services
    product = ProductService(engine).list_products()[0]
    service = ReceiptService(engine)
    created = service.create_receipt(
        "Cliente",
        [ReceiptLine(product.id, Decimal("1"), product.wholesale_price)],
    )
    with pytest.raises(ValueError, match="motivo"):
        service.update_receipt(
            created.id,
            "",
            "Cliente",
            [ReceiptLine(product.id, Decimal("2"), product.wholesale_price)],
        )
    updated = service.update_receipt(
        created.id,
        "Corrección de cantidad",
        "Cliente",
        [ReceiptLine(product.id, Decimal("2"), product.wholesale_price)],
        amount_paid=product.wholesale_price * 2,
    )
    assert updated.total == product.wholesale_price * 2
    assert len(service.get_receipt(created.id).revisions) == 2


def test_cancel_receipt_requires_reason(services) -> None:  # type: ignore[no-untyped-def]
    engine, _ = services
    product = ProductService(engine).list_products()[0]
    service = ReceiptService(engine)
    created = service.create_receipt(
        "Cliente",
        [ReceiptLine(product.id, Decimal("1"), product.wholesale_price)],
    )
    with pytest.raises(ValueError, match="motivo"):
        service.cancel_receipt(created.id, "")
    service.cancel_receipt(created.id, "Venta anulada")
    assert service.get_receipt(created.id).status == "cancelled"


def test_price_batch_can_be_reverted(services) -> None:  # type: ignore[no-untyped-def]
    engine, _ = services
    service = PriceService(engine)
    preview = service.preview(operation="increase_percentage", value=Decimal("10"))[:2]
    old_prices = {row.product_id: row.old_price for row in preview}
    batch = service.apply(
        preview,
        description="Prueba",
        operation="increase_percentage",
        value=Decimal("10"),
        target_type="selection",
    )
    assert batch.products_affected == 2
    assert service.revert_batch(batch.id) == 2
    current = {row.id: row.wholesale_price for row in ProductService(engine).list_products()}
    assert all(current[product_id] == price for product_id, price in old_prices.items())


def test_csv_import_preview_and_commit(services, tmp_path) -> None:  # type: ignore[no-untyped-def]
    engine, database_path = services
    source = tmp_path / "lista.csv"
    source.write_text(
        "Proveedor;Producto;Presentación;Precio\nProveedor Nuevo;Producto Nuevo;Unidad;1250\n",
        encoding="utf-8",
    )
    backup_service = BackupService(database_path, tmp_path / "backups")
    backup = backup_service.create_backup("before_import")
    assert backup.exists()
    service = PriceListImportService(engine, tmp_path / "imports")
    preview = service.preview_file(source)
    assert preview.rows[0].action == "create"
    result = service.commit_preview(preview)
    assert result.created == 1
    assert any(row.name == "Producto Nuevo" for row in ProductService(engine).list_products())
