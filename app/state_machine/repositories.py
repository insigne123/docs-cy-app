"""Consultas de apoyo para los guards (entidades polimórficas contrato/licitación)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import DocumentoTipo, GarantiaEstado, GarantiaTipo
from app.models.contrato import Documento, Garantia
from app.models.evento import EventoEstado

_GARANTIAS_DE_CUMPLIMIENTO = (GarantiaTipo.fiel_cumplimiento, GarantiaTipo.correcta_ejecucion)


def eventos_de(session: Session, entidad_tipo: str, entidad_id: int) -> list[EventoEstado]:
    stmt = (
        select(EventoEstado)
        .where(EventoEstado.entidad_tipo == entidad_tipo, EventoEstado.entidad_id == entidad_id)
        .order_by(EventoEstado.fecha, EventoEstado.id)
    )
    return list(session.scalars(stmt))


def tiene_documento(session: Session, entidad_tipo: str, entidad_id: int, tipo: DocumentoTipo) -> bool:
    stmt = select(Documento.id).where(
        Documento.entidad_tipo == entidad_tipo,
        Documento.entidad_id == entidad_id,
        Documento.tipo == tipo,
    )
    return session.scalars(stmt).first() is not None


def tiene_garantia(
    session: Session, entidad_tipo: str, entidad_id: int, tipo: GarantiaTipo
) -> bool:
    stmt = select(Garantia.id).where(
        Garantia.entidad_tipo == entidad_tipo,
        Garantia.entidad_id == entidad_id,
        Garantia.tipo == tipo,
    )
    return session.scalars(stmt).first() is not None


def tiene_garantia_cumplimiento_vigente(
    session: Session, entidad_tipo: str, entidad_id: int
) -> bool:
    stmt = select(Garantia.id).where(
        Garantia.entidad_tipo == entidad_tipo,
        Garantia.entidad_id == entidad_id,
        Garantia.tipo.in_(_GARANTIAS_DE_CUMPLIMIENTO),
        Garantia.estado == GarantiaEstado.vigente,
    )
    return session.scalars(stmt).first() is not None
