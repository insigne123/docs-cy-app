"""Trazabilidad: una fila inmutable por cada cambio de estado."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventoEstado(Base):
    __tablename__ = "evento_estado"
    __table_args__ = (Index("ix_evento_entidad", "entidad_tipo", "entidad_id", "fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entidad_tipo: Mapped[str] = mapped_column(String(20))  # "contrato" | "licitacion"
    entidad_id: Mapped[int] = mapped_column(Integer)
    estado_origen: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado_destino: Mapped[str] = mapped_column(String(50))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"))
    rol_actor: Mapped[str] = mapped_column(String(40))
    comentario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retorno_a: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    documento_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
