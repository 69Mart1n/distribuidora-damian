from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.database.connection import build_session_factory, session_scope
from app.database.models import PriceHistory, PriceUpdateBatch, Product
from app.utils.money import require_whole_number, to_money, to_pesos

OPERATIONS = {
    "increase_percentage",
    "decrease_percentage",
    "add_fixed_amount",
    "subtract_fixed_amount",
}


@dataclass
class PriceChangePreview:
    product_id: int
    code: str
    product: str
    presentation: str
    supplier: str
    old_price: Decimal
    new_price: Decimal
    included: bool = True

    @property
    def difference(self) -> Decimal:
        return to_money(self.new_price - self.old_price)


@dataclass(frozen=True)
class PriceBatchSummary:
    id: int
    description: str
    operation: str
    products_affected: int
    applied_at: datetime
    active: bool


class PriceService:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = build_session_factory(engine)

    def preview(
        self,
        *,
        operation: str,
        value: Decimal,
        supplier_id: int | None = None,
        category_id: int | None = None,
        product_ids: list[int] | None = None,
    ) -> list[PriceChangePreview]:
        self._validate_operation(operation, value)
        with session_scope(self._session_factory) as session:
            statement = select(Product).where(
                Product.active.is_(True),
                Product.wholesale_price.is_not(None),
            )
            if supplier_id:
                statement = statement.where(Product.supplier_id == supplier_id)
            if category_id:
                statement = statement.where(Product.category_id == category_id)
            if product_ids:
                statement = statement.where(Product.id.in_(product_ids))
            products = session.scalars(statement.order_by(Product.name)).all()
            return [
                PriceChangePreview(
                    product.id,
                    product.internal_code or "",
                    product.name,
                    product.presentation,
                    product.supplier.name,
                    product.wholesale_price,
                    self._calculate(product.wholesale_price, operation, value),
                )
                for product in products
            ]

    def apply(
        self,
        changes: list[PriceChangePreview],
        *,
        description: str,
        operation: str,
        value: Decimal,
        target_type: str,
        supplier_id: int | None = None,
        category_id: int | None = None,
    ) -> PriceBatchSummary:
        self._validate_operation(operation, value)
        included = [change for change in changes if change.included]
        if not included:
            raise ValueError("Selecciona al menos un producto.")
        with session_scope(self._session_factory) as session:
            batch = PriceUpdateBatch(
                description=description.strip() or "Actualización de precios",
                target_type=target_type,
                supplier_id=supplier_id,
                category_id=category_id,
                percentage=value if "percentage" in operation else None,
                fixed_amount=to_money(value) if "fixed_amount" in operation else None,
                operation=operation,
                price_type="wholesale",
                rounding_rule="peso_entero",
                products_affected=len(included),
            )
            session.add(batch)
            session.flush()
            for change in included:
                product = session.get(Product, change.product_id)
                if product is None or not product.active or product.wholesale_price is None:
                    raise ValueError(f"El producto {change.product} ya no está disponible.")
                if product.wholesale_price != change.old_price:
                    raise ValueError(
                        f"El precio de {change.product} cambio desde la vista previa. "
                        "Actualiza la lista."
                    )
                product.wholesale_price = to_money(change.new_price)
                session.add(
                    PriceHistory(
                        product_id=product.id,
                        price_type="wholesale",
                        old_price=change.old_price,
                        new_price=change.new_price,
                        percentage_change=value if "percentage" in operation else None,
                        fixed_change=value if "fixed_amount" in operation else None,
                        change_source="batch",
                        supplier_id=product.supplier_id,
                        batch_id=batch.id,
                        reason=batch.description,
                    )
                )
            session.flush()
            return PriceBatchSummary(
                batch.id,
                batch.description,
                batch.operation,
                batch.products_affected,
                batch.applied_at,
                batch.active,
            )

    def list_batches(self) -> list[PriceBatchSummary]:
        with session_scope(self._session_factory) as session:
            batches = session.scalars(
                select(PriceUpdateBatch).order_by(PriceUpdateBatch.applied_at.desc())
            ).all()
            return [
                PriceBatchSummary(
                    row.id,
                    row.description,
                    row.operation,
                    row.products_affected,
                    row.applied_at,
                    row.active,
                )
                for row in batches
            ]

    def revert_batch(self, batch_id: int) -> int:
        with session_scope(self._session_factory) as session:
            batch = session.get(PriceUpdateBatch, batch_id)
            if batch is None or not batch.active:
                raise ValueError("El lote ya no está disponible para deshacer.")
            histories = session.scalars(
                select(PriceHistory)
                .where(PriceHistory.batch_id == batch.id)
                .order_by(PriceHistory.id.desc())
            ).all()
            if not histories:
                raise ValueError("El lote no tiene cambios registrados.")
            for history in histories:
                product = session.get(Product, history.product_id)
                if product is None:
                    continue
                current = product.wholesale_price
                product.wholesale_price = history.old_price
                session.add(
                    PriceHistory(
                        product_id=product.id,
                        price_type="wholesale",
                        old_price=current,
                        new_price=history.old_price,
                        change_source="rollback",
                        reason=f"Deshacer lote: {batch.description}",
                    )
                )
            batch.active = False
            batch.reverted_at = datetime.now()
            return len(histories)

    @staticmethod
    def _validate_operation(operation: str, value: Decimal) -> None:
        if operation not in OPERATIONS:
            raise ValueError("La operación seleccionada no es válida.")
        if value <= 0:
            raise ValueError("El valor debe ser mayor a cero.")
        if "percentage" in operation and value > 1000:
            raise ValueError("El porcentaje es demasiado alto.")
        if "fixed_amount" in operation:
            require_whole_number(value, "El monto")

    @staticmethod
    def _calculate(old_price: Decimal, operation: str, value: Decimal) -> Decimal:
        if operation == "increase_percentage":
            calculated = old_price * (Decimal("1") + value / Decimal("100"))
        elif operation == "decrease_percentage":
            calculated = old_price * (Decimal("1") - value / Decimal("100"))
        elif operation == "add_fixed_amount":
            calculated = old_price + value
        else:
            calculated = old_price - value
        if calculated <= 0:
            raise ValueError("La operación produciría un precio menor o igual a cero.")
        return to_money(to_pesos(calculated))
