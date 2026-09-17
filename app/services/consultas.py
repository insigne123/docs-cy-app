"""Consultas de lectura reutilizadas por la API y el panel web."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contrato import Contrato, Documento, Garantia
from app.models.licitacion import Licitacion
from app.state_machine import MotorEstados


def _garantias(session: Session, entidad_tipo: str, entidad_id: int):
    return session.scalars(
        select(Garantia).where(
            Garantia.entidad_tipo == entidad_tipo, Garantia.entidad_id == entidad_id
        )
    ).all()


def _documentos(session: Session, entidad_tipo: str, entidad_id: int):
    return session.scalars(
        select(Documento).where(
            Documento.entidad_tipo == entidad_tipo, Documento.entidad_id == entidad_id
        )
    ).all()


def ficha_contrato(session: Session, contrato: Contrato) -> dict:
    return {
        "contrato": contrato,
        "garantias": _garantias(session, "contrato", contrato.id),
        "hitos": contrato.hitos,
        "multas": contrato.multas,
        "documentos": _documentos(session, "contrato", contrato.id),
        "historial": MotorEstados(session).historial(contrato),
    }


def ficha_licitacion(session: Session, licitacion: Licitacion) -> dict:
    return {
        "licitacion": licitacion,
        "garantias": _garantias(session, "licitacion", licitacion.id),
        "documentos": _documentos(session, "licitacion", licitacion.id),
        "historial": MotorEstados(session).historial(licitacion),
    }
