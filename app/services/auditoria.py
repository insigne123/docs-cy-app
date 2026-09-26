"""Registro de auditoría a nivel sistema: todos los cambios de estado de
todos los contratos y licitaciones, no solo los de una ficha individual."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contrato import Contrato
from app.models.core import Usuario
from app.models.evento import EventoEstado
from app.models.licitacion import Licitacion

LIMITE = 200


def historial_global(
    session: Session,
    *,
    usuario_id: Optional[int] = None,
    entidad_tipo: Optional[str] = None,
    limite: int = LIMITE,
) -> list[dict]:
    stmt = select(EventoEstado).order_by(EventoEstado.fecha.desc(), EventoEstado.id.desc())
    if usuario_id:
        stmt = stmt.where(EventoEstado.usuario_id == usuario_id)
    if entidad_tipo:
        stmt = stmt.where(EventoEstado.entidad_tipo == entidad_tipo)
    eventos = list(session.scalars(stmt.limit(limite)))

    nombres_usuario = {u.id: u.nombre for u in session.scalars(select(Usuario))}
    codigos_contrato = {c.id: c.codigo for c in session.scalars(select(Contrato))}
    codigos_licitacion = {l.id: l.codigo for l in session.scalars(select(Licitacion))}

    def codigo_de(e: EventoEstado) -> str:
        tabla = codigos_contrato if e.entidad_tipo == "contrato" else codigos_licitacion
        return tabla.get(e.entidad_id, f"{e.entidad_tipo} {e.entidad_id}")

    return [
        {
            "id": e.id,
            "fecha": e.fecha,
            "entidad_tipo": e.entidad_tipo,
            "entidad_id": e.entidad_id,
            "codigo": codigo_de(e),
            "estado_origen": e.estado_origen,
            "estado_destino": e.estado_destino,
            "usuario_id": e.usuario_id,
            "usuario_nombre": nombres_usuario.get(e.usuario_id, f"usuario {e.usuario_id}"),
            "rol_actor": e.rol_actor,
            "comentario": e.comentario,
        }
        for e in eventos
    ]
