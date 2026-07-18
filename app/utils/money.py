from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MONEY_QUANT = Decimal("0.01")
PESO_QUANT = Decimal("1")


def to_money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def to_pesos(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(PESO_QUANT, rounding=ROUND_HALF_UP)


def require_whole_number(
    value: Decimal | int | str,
    field_name: str,
    *,
    allow_zero: bool = False,
) -> Decimal:
    decimal_value = Decimal(str(value))
    minimum = Decimal("0") if allow_zero else Decimal("1")
    if decimal_value < minimum:
        qualifier = "cero o mayor" if allow_zero else "mayor a cero"
        raise ValueError(f"{field_name} debe ser {qualifier}.")
    if decimal_value != decimal_value.to_integral_value():
        raise ValueError(f"{field_name} debe ser un número entero, sin decimales.")
    return decimal_value


def format_money(value: Decimal | None, symbol: str = "$") -> str:
    if value is None:
        return "Sin precio"
    amount = to_pesos(value)
    return f"{symbol} {amount:,.0f}".replace(",", ".")
