from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Settings


class SettingsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_settings(self) -> Settings:
        settings = self._session.scalar(select(Settings).where(Settings.id == 1))
        if settings is None:
            raise RuntimeError("No se encontró la configuración inicial.")
        return settings
