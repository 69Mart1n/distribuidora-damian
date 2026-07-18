from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from app.database.connection import build_session_factory, session_scope
from app.database.models import Settings


@dataclass(frozen=True)
class BusinessSettings:
    business_name: str
    phone: str
    address: str
    email: str
    receipt_prefix: str
    next_receipt_number: int
    logo_path: str
    currency_symbol: str
    backup_enabled: bool
    backup_retention_days: int
    monthly_retention_count: int
    exports_path: str
    backups_path: str
    theme: str


class SettingsService:
    def __init__(self, engine: Engine) -> None:
        self._session_factory = build_session_factory(engine)

    def get(self) -> BusinessSettings:
        with session_scope(self._session_factory) as session:
            settings = session.get(Settings, 1)
            if settings is None:
                raise RuntimeError("No se encontró la configuración.")
            return BusinessSettings(
                settings.business_name,
                settings.business_phone or "",
                settings.business_address or "",
                settings.business_email or "",
                settings.receipt_prefix,
                settings.next_receipt_number,
                settings.business_logo_path or "",
                settings.currency_symbol,
                settings.backup_enabled,
                settings.backup_retention_days,
                settings.monthly_retention_count,
                settings.exports_path or "",
                settings.backups_path or "",
                settings.theme,
            )

    def save(
        self,
        business_name: str,
        phone: str,
        address: str,
        email: str,
        receipt_prefix: str,
        next_receipt_number: int,
        *,
        logo_path: str = "",
        currency_symbol: str = "$",
        backup_enabled: bool = True,
        backup_retention_days: int = 30,
        monthly_retention_count: int = 12,
        exports_path: str = "",
        backups_path: str = "",
        theme: str = "light",
    ) -> BusinessSettings:
        clean_name = business_name.strip()
        clean_prefix = receipt_prefix.strip().upper()
        if not clean_name:
            raise ValueError("Ingresa el nombre del negocio.")
        if not clean_prefix or len(clean_prefix) > 12:
            raise ValueError("El prefijo debe tener entre 1 y 12 caracteres.")
        if next_receipt_number < 500:
            raise ValueError("El próximo número de boleta no puede ser menor a 500.")
        with session_scope(self._session_factory) as session:
            settings = session.get(Settings, 1)
            if settings is None:
                raise RuntimeError("No se encontró la configuración.")
            settings.business_name = clean_name
            settings.business_phone = phone.strip() or None
            settings.business_address = address.strip() or None
            settings.business_email = email.strip() or None
            settings.receipt_prefix = clean_prefix
            settings.next_receipt_number = next_receipt_number
            settings.business_logo_path = logo_path.strip() or None
            settings.currency_symbol = currency_symbol.strip() or "$"
            settings.backup_enabled = backup_enabled
            settings.backup_retention_days = backup_retention_days
            settings.monthly_retention_count = monthly_retention_count
            settings.exports_path = exports_path.strip() or None
            settings.backups_path = backups_path.strip() or None
            settings.theme = theme
        return self.get()
