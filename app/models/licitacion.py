"""Licitaciones (Línea C — Fase I). La Fase II vive en el contrato asociado."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import EstadoLicitacion, LicitacionFase, LicitacionResultado, Moneda
from app.models.base import Base, TimestampMixin, enum_col


class Licitacion(Base, TimestampMixin):
    __tablename__ = "licitacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)
    codigo_externo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    objeto: Mapped[str] = mapped_column(Text)
    mandante: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contraparte_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contraparte.id"), nullable=True)
    unidad_solicitante_id: Mapped[int] = mapped_column(ForeignKey("unidad.id"))

    fase: Mapped[LicitacionFase] = mapped_column(
        enum_col(LicitacionFase), default=LicitacionFase.pre_adjudicacion
    )
    estado: Mapped[EstadoLicitacion] = mapped_column(enum_col(EstadoLicitacion))

    fecha_publicacion_bases: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_ingreso: Mapped[date] = mapped_column(Date)
    fecha_cierre_ofertas: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_apertura: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    presupuesto_referencia: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    moneda: Mapped[Optional[Moneda]] = mapped_column(enum_col(Moneda), nullable=True)
    exige_garantia_seriedad: Mapped[bool] = mapped_column(Boolean, default=False)

    resultado: Mapped[LicitacionResultado] = mapped_column(
        enum_col(LicitacionResultado), default=LicitacionResultado.en_proceso
    )
    fecha_resultado: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # FK lógica a contrato.id (evita FK circular con contrato.licitacion_id).
    contrato_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    informe_riesgos_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    analisis_interno: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
