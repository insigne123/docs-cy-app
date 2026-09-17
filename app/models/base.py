"""Base declarativa y utilidades comunes de los modelos."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def enum_col(py_enum: type[enum.Enum]) -> SAEnum:
    """Columna de enumeración portable (VARCHAR + CHECK), válida en SQLite y PostgreSQL."""
    return SAEnum(
        py_enum,
        native_enum=False,
        length=50,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


class TimestampMixin:
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
