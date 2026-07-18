from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.engine import Engine

from app.database.connection import build_session_factory, session_scope
from app.database.models import Customer, Receipt
from app.utils.money import to_money


@dataclass(frozen=True)
class CustomerSummary:
    id: int
    name: str
    phone: str
    address: str
    document: str
    notes: str
    active: bool
    receipts_count: int = 0
    total_purchased: Decimal = Decimal("0.00")
    pending_balance: Decimal = Decimal("0.00")


class CustomerService:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = build_session_factory(engine)

    def list_customers(
        self, search: str = "", *, include_inactive: bool = False
    ) -> list[CustomerSummary]:
        with session_scope(self._session_factory) as session:
            totals = (
                select(
                    Receipt.customer_id.label("customer_id"),
                    func.count(Receipt.id).label("receipts_count"),
                    func.coalesce(func.sum(Receipt.total), 0).label("total_purchased"),
                    func.coalesce(func.sum(Receipt.pending_amount), 0).label("pending_balance"),
                )
                .where(Receipt.status == "active")
                .group_by(Receipt.customer_id)
                .subquery()
            )
            statement = (
                select(
                    Customer,
                    func.coalesce(totals.c.receipts_count, 0),
                    func.coalesce(totals.c.total_purchased, 0),
                    func.coalesce(totals.c.pending_balance, 0),
                )
                .outerjoin(totals, totals.c.customer_id == Customer.id)
                .order_by(Customer.name.asc())
            )
            if not include_inactive:
                statement = statement.where(Customer.active.is_(True))
            if search.strip():
                like = f"%{search.strip()}%"
                statement = statement.where(
                    or_(
                        Customer.name.like(like),
                        Customer.phone.like(like),
                        Customer.document.like(like),
                    )
                )
            return [
                self._summary(customer, count, purchased, pending)
                for customer, count, purchased, pending in session.execute(statement).all()
            ]

    def get_customer(self, customer_id: int) -> CustomerSummary:
        rows = self.list_customers(include_inactive=True)
        customer = next((row for row in rows if row.id == customer_id), None)
        if customer is None:
            raise ValueError("No se encontró el cliente.")
        return customer

    def save_customer(
        self,
        customer_id: int | None,
        name: str,
        phone: str,
        address: str,
        document: str,
        notes: str = "",
    ) -> CustomerSummary:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Ingresa el nombre del cliente.")
        if len(clean_name) > 180:
            raise ValueError("El nombre del cliente es demasiado largo.")
        with session_scope(self._session_factory) as session:
            customer = session.get(Customer, customer_id) if customer_id else Customer(name="")
            if customer is None:
                raise ValueError("El cliente ya no existe.")
            customer.name = clean_name
            customer.phone = phone.strip() or None
            customer.address = address.strip() or None
            customer.document = document.strip() or None
            customer.notes = notes.strip() or None
            customer.active = True
            session.add(customer)
            session.flush()
            return self._summary(customer, 0, Decimal("0"), Decimal("0"))

    def set_active(self, customer_id: int, active: bool) -> None:
        with session_scope(self._session_factory) as session:
            customer = session.get(Customer, customer_id)
            if customer is None:
                raise ValueError("No se encontró el cliente.")
            customer.active = active

    @staticmethod
    def _summary(
        customer: Customer,
        count: int,
        purchased: Decimal,
        pending: Decimal,
    ) -> CustomerSummary:
        return CustomerSummary(
            id=customer.id,
            name=customer.name,
            phone=customer.phone or "",
            address=customer.address or "",
            document=customer.document or "",
            notes=customer.notes or "",
            active=customer.active,
            receipts_count=int(count),
            total_purchased=to_money(purchased),
            pending_balance=to_money(pending),
        )
