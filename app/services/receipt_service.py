from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import selectinload

from app.database.connection import build_session_factory, session_scope
from app.database.models import (
    Customer,
    Product,
    Receipt,
    ReceiptItem,
    ReceiptPayment,
    ReceiptRevision,
    ReceiptRevisionItem,
    Settings,
)
from app.utils.money import require_whole_number, to_money

PAYMENT_METHODS = {"cash", "transfer", "account", "mixed"}


@dataclass(frozen=True)
class ReceiptLine:
    product_id: int
    quantity: Decimal
    unit_price: Decimal


@dataclass(frozen=True)
class PaymentInput:
    payment_method: str
    amount: Decimal
    notes: str = ""


@dataclass(frozen=True)
class CreatedReceipt:
    id: int
    receipt_code: str
    total: Decimal
    payment_status: str
    pending_amount: Decimal


@dataclass(frozen=True)
class ReceiptSummary:
    id: int
    receipt_code: str
    customer_name: str
    customer_phone: str
    issued_at: datetime
    total: Decimal
    amount_paid: Decimal
    pending_amount: Decimal
    payment_method: str
    payment_status: str
    status: str


@dataclass(frozen=True)
class DuplicateReceiptData:
    customer_id: int | None
    customer_name: str
    notes: str
    lines: tuple[ReceiptLine, ...]


class ReceiptService:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = build_session_factory(engine)

    def create_receipt(
        self,
        customer_name: str,
        lines: list[ReceiptLine],
        *,
        customer_id: int | None = None,
        payments: list[PaymentInput] | None = None,
        payment_method: str = "cash",
        amount_paid: Decimal | None = None,
        notes: str = "",
    ) -> CreatedReceipt:
        if not lines:
            raise ValueError("Agrega al menos un producto.")
        with session_scope(self._session_factory) as session:
            settings = session.get(Settings, 1)
            if settings is None:
                raise RuntimeError("No se encontró la configuración inicial.")
            customer, snapshots = self._customer_snapshots(session, customer_id, customer_name)
            prepared_lines, total = self._prepare_lines(session, lines)
            normalized_payments, method, paid, pending, payment_status = self._prepare_payments(
                total,
                payments,
                payment_method,
                total if amount_paid is None and payments is None else amount_paid,
            )
            receipt_number = settings.next_receipt_number
            receipt = Receipt(
                receipt_number=receipt_number,
                receipt_code=f"{settings.receipt_prefix}-{receipt_number:06d}",
                customer_id=customer.id if customer else None,
                customer_name_snapshot=snapshots[0],
                customer_phone_snapshot=snapshots[1],
                customer_address_snapshot=snapshots[2],
                subtotal=total,
                total=total,
                payment_method=method,
                payment_status=payment_status,
                amount_paid=paid,
                pending_amount=pending,
                notes=notes.strip() or None,
            )
            session.add(receipt)
            session.flush()
            self._replace_items(receipt, prepared_lines)
            self._replace_payments(receipt, normalized_payments)
            session.flush()
            self._create_revision(session, receipt, "Creacion de boleta")
            settings.next_receipt_number += 1
            session.flush()
            return CreatedReceipt(
                receipt.id,
                receipt.receipt_code,
                receipt.total,
                receipt.payment_status,
                receipt.pending_amount,
            )

    def update_receipt(
        self,
        receipt_id: int,
        reason: str,
        customer_name: str,
        lines: list[ReceiptLine],
        *,
        customer_id: int | None = None,
        payments: list[PaymentInput] | None = None,
        payment_method: str = "cash",
        amount_paid: Decimal | None = None,
        notes: str = "",
    ) -> CreatedReceipt:
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("Ingresa el motivo de la edición.")
        if not lines:
            raise ValueError("Agrega al menos un producto.")
        with session_scope(self._session_factory) as session:
            receipt = self._receipt_for_update(session, receipt_id)
            if receipt.status == "cancelled":
                raise ValueError("No se puede editar una boleta cancelada.")
            customer, snapshots = self._customer_snapshots(session, customer_id, customer_name)
            prepared_lines, total = self._prepare_lines(session, lines)
            normalized_payments, method, paid, pending, payment_status = self._prepare_payments(
                total,
                payments,
                payment_method,
                amount_paid,
            )
            receipt.customer_id = customer.id if customer else None
            receipt.customer_name_snapshot = snapshots[0]
            receipt.customer_phone_snapshot = snapshots[1]
            receipt.customer_address_snapshot = snapshots[2]
            receipt.subtotal = total
            receipt.total = total
            receipt.payment_method = method
            receipt.payment_status = payment_status
            receipt.amount_paid = paid
            receipt.pending_amount = pending
            receipt.notes = notes.strip() or None
            self._replace_items(receipt, prepared_lines)
            self._replace_payments(receipt, normalized_payments)
            session.flush()
            self._create_revision(session, receipt, clean_reason)
            return CreatedReceipt(
                receipt.id,
                receipt.receipt_code,
                receipt.total,
                receipt.payment_status,
                receipt.pending_amount,
            )

    def register_payment(
        self,
        receipt_id: int,
        payment_method: str,
        amount: Decimal,
        notes: str = "",
    ) -> CreatedReceipt:
        clean_amount = to_money(require_whole_number(amount, "El importe"))
        self._validate_payment_method(payment_method)
        with session_scope(self._session_factory) as session:
            receipt = self._receipt_for_update(session, receipt_id)
            if receipt.status == "cancelled":
                raise ValueError("No se puede registrar un pago en una boleta cancelada.")
            if clean_amount > receipt.pending_amount:
                raise ValueError("El pago no puede superar el saldo pendiente.")
            receipt.payments.append(
                ReceiptPayment(
                    payment_method=payment_method,
                    amount=clean_amount,
                    notes=notes.strip() or None,
                )
            )
            receipt.amount_paid = to_money(receipt.amount_paid + clean_amount)
            receipt.pending_amount = to_money(receipt.total - receipt.amount_paid)
            receipt.payment_status = "paid" if receipt.pending_amount == 0 else "partial"
            methods = {payment.payment_method for payment in receipt.payments if payment.active}
            receipt.payment_method = next(iter(methods)) if len(methods) == 1 else "mixed"
            session.flush()
            self._create_revision(session, receipt, "Registro de pago")
            return CreatedReceipt(
                receipt.id,
                receipt.receipt_code,
                receipt.total,
                receipt.payment_status,
                receipt.pending_amount,
            )

    def cancel_receipt(self, receipt_id: int, reason: str) -> None:
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("Ingresa el motivo de la cancelación.")
        with session_scope(self._session_factory) as session:
            receipt = self._receipt_for_update(session, receipt_id)
            if receipt.status == "cancelled":
                raise ValueError("La boleta ya esta cancelada.")
            receipt.status = "cancelled"
            receipt.cancelled_at = datetime.now(UTC)
            receipt.cancellation_reason = clean_reason
            session.flush()
            self._create_revision(session, receipt, f"Cancelación: {clean_reason}")

    def duplicate_data(self, receipt_id: int) -> DuplicateReceiptData:
        receipt = self.get_receipt(receipt_id)
        return DuplicateReceiptData(
            customer_id=receipt.customer_id,
            customer_name=receipt.customer_name_snapshot,
            notes=receipt.notes or "",
            lines=tuple(
                ReceiptLine(item.product_id, item.quantity, item.unit_price)
                for item in receipt.items
                if item.product_id is not None
            ),
        )

    def list_receipts(
        self,
        search: str = "",
        *,
        payment_status: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[ReceiptSummary]:
        with session_scope(self._session_factory) as session:
            statement = select(Receipt).order_by(Receipt.issued_at.desc(), Receipt.id.desc())
            if search.strip():
                like = f"%{search.strip()}%"
                statement = statement.where(
                    or_(
                        Receipt.receipt_code.like(like),
                        Receipt.customer_name_snapshot.like(like),
                        Receipt.customer_phone_snapshot.like(like),
                    )
                )
            if payment_status:
                statement = statement.where(Receipt.payment_status == payment_status)
            if status:
                statement = statement.where(Receipt.status == status)
            if date_from:
                statement = statement.where(Receipt.issued_at >= date_from)
            if date_to:
                statement = statement.where(Receipt.issued_at <= date_to)
            return [self._summary(receipt) for receipt in session.scalars(statement).all()]

    def get_receipt(self, receipt_id: int) -> Receipt:
        with session_scope(self._session_factory) as session:
            receipt = session.scalar(
                select(Receipt)
                .where(Receipt.id == receipt_id)
                .options(
                    selectinload(Receipt.items),
                    selectinload(Receipt.payments),
                    selectinload(Receipt.revisions).selectinload(ReceiptRevision.items),
                )
            )
            if receipt is None:
                raise ValueError("No se encontró la boleta.")
            session.expunge_all()
            return receipt

    @staticmethod
    def _summary(receipt: Receipt) -> ReceiptSummary:
        return ReceiptSummary(
            id=receipt.id,
            receipt_code=receipt.receipt_code,
            customer_name=receipt.customer_name_snapshot,
            customer_phone=receipt.customer_phone_snapshot or "",
            issued_at=receipt.issued_at,
            total=receipt.total,
            amount_paid=receipt.amount_paid,
            pending_amount=receipt.pending_amount,
            payment_method=receipt.payment_method,
            payment_status=receipt.payment_status,
            status=receipt.status,
        )

    @staticmethod
    def _customer_snapshots(
        session,  # type: ignore[no-untyped-def]
        customer_id: int | None,
        customer_name: str,
    ) -> tuple[Customer | None, tuple[str, str | None, str | None]]:
        if customer_id is not None:
            customer = session.get(Customer, customer_id)
            if customer is None or not customer.active:
                raise ValueError("El cliente seleccionado ya no está disponible.")
            return customer, (customer.name, customer.phone, customer.address)
        clean_name = customer_name.strip() or "Cliente ocasional"
        if len(clean_name) > 180:
            raise ValueError("El nombre del cliente es demasiado largo.")
        return None, (clean_name, None, None)

    @staticmethod
    def _prepare_lines(
        session,  # type: ignore[no-untyped-def]
        lines: list[ReceiptLine],
    ) -> tuple[list[tuple[Product, Decimal, Decimal, Decimal]], Decimal]:
        prepared: list[tuple[Product, Decimal, Decimal, Decimal]] = []
        total = Decimal("0.00")
        for line in lines:
            quantity = require_whole_number(line.quantity, "La cantidad")
            unit_price = to_money(require_whole_number(line.unit_price, "El precio"))
            product = session.get(Product, line.product_id)
            if product is None or not product.active:
                raise ValueError("Uno de los productos ya no está disponible.")
            line_total = to_money(quantity * unit_price)
            prepared.append((product, quantity, unit_price, line_total))
            total += line_total
        return prepared, to_money(total)

    @classmethod
    def _prepare_payments(
        cls,
        total: Decimal,
        payments: list[PaymentInput] | None,
        payment_method: str,
        amount_paid: Decimal | None,
    ) -> tuple[list[PaymentInput], str, Decimal, Decimal, str]:
        if payments is None:
            cls._validate_payment_method(payment_method)
            paid = (
                Decimal("0")
                if amount_paid is None
                else require_whole_number(
                    amount_paid,
                    "El importe pagado",
                    allow_zero=True,
                )
            )
            payments = [PaymentInput(payment_method, to_money(paid))] if paid > 0 else []
            fallback_method = payment_method
        else:
            fallback_method = payment_method
            normalized: list[PaymentInput] = []
            for payment in payments:
                cls._validate_payment_method(payment.payment_method)
                amount = require_whole_number(
                    payment.amount,
                    "El importe pagado",
                    allow_zero=True,
                )
                if amount > 0:
                    normalized.append(
                        PaymentInput(payment.payment_method, to_money(amount), payment.notes)
                    )
            payments = normalized
        paid_total = to_money(sum((payment.amount for payment in payments), Decimal("0")))
        if paid_total > total:
            raise ValueError("El importe pagado no puede superar el total.")
        pending = to_money(total - paid_total)
        status = "paid" if pending == 0 else "pending" if paid_total == 0 else "partial"
        methods = {payment.payment_method for payment in payments}
        method = (
            next(iter(methods)) if len(methods) == 1 else "mixed" if methods else fallback_method
        )
        return payments, method, paid_total, pending, status

    @staticmethod
    def _replace_items(
        receipt: Receipt,
        prepared: list[tuple[Product, Decimal, Decimal, Decimal]],
    ) -> None:
        receipt.items.clear()
        for product, quantity, unit_price, line_total in prepared:
            receipt.items.append(
                ReceiptItem(
                    product_id=product.id,
                    product_code_snapshot=product.internal_code,
                    product_name_snapshot=product.name,
                    presentation_snapshot=product.presentation,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_percentage=Decimal("0"),
                    discount_amount=Decimal("0.00"),
                    line_subtotal=line_total,
                    line_total=line_total,
                )
            )

    @staticmethod
    def _replace_payments(receipt: Receipt, payments: list[PaymentInput]) -> None:
        receipt.payments.clear()
        for payment in payments:
            receipt.payments.append(
                ReceiptPayment(
                    payment_method=payment.payment_method,
                    amount=payment.amount,
                    notes=payment.notes.strip() or None,
                )
            )

    @staticmethod
    def _receipt_for_update(session, receipt_id: int) -> Receipt:  # type: ignore[no-untyped-def]
        receipt = session.scalar(
            select(Receipt)
            .where(Receipt.id == receipt_id)
            .options(
                selectinload(Receipt.items),
                selectinload(Receipt.payments),
                selectinload(Receipt.revisions),
            )
        )
        if receipt is None:
            raise ValueError("No se encontró la boleta.")
        return receipt

    @staticmethod
    def _create_revision(session, receipt: Receipt, reason: str) -> None:  # type: ignore[no-untyped-def]
        latest = max((revision.revision_number for revision in receipt.revisions), default=0)
        revision = ReceiptRevision(
            receipt_id=receipt.id,
            revision_number=latest + 1,
            reason=reason,
            customer_name_snapshot=receipt.customer_name_snapshot,
            customer_phone_snapshot=receipt.customer_phone_snapshot,
            customer_address_snapshot=receipt.customer_address_snapshot,
            payment_method=receipt.payment_method,
            payment_status=receipt.payment_status,
            amount_paid=receipt.amount_paid,
            pending_amount=receipt.pending_amount,
            total=receipt.total,
            notes=receipt.notes,
            status=receipt.status,
        )
        session.add(revision)
        session.flush()
        for item in receipt.items:
            revision.items.append(
                ReceiptRevisionItem(
                    product_id=item.product_id,
                    product_code_snapshot=item.product_code_snapshot,
                    product_name_snapshot=item.product_name_snapshot,
                    presentation_snapshot=item.presentation_snapshot,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
            )

    @staticmethod
    def _validate_payment_method(payment_method: str) -> None:
        if payment_method not in PAYMENT_METHODS:
            raise ValueError("La forma de pago no es válida.")
