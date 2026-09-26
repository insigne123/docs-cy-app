"""Notas libres en la ficha de un contrato o licitación — bitácora aparte de
los cambios de estado, para dejar contexto que no encaja en un comentario de
transición (EventoEstado.comentario)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contrato import Comentario
from app.models.core import Usuario


def listar_comentarios(session: Session, entidad_tipo: str, entidad_id: int) -> list[dict]:
    comentarios = session.scalars(
        select(Comentario)
        .where(Comentario.entidad_tipo == entidad_tipo, Comentario.entidad_id == entidad_id)
        .order_by(Comentario.creado_en.desc())
    )
    nombres = {u.id: u.nombre for u in session.scalars(select(Usuario))}
    return [
        {
            "id": c.id,
            "texto": c.texto,
            "usuario": nombres.get(c.usuario_id, f"usuario {c.usuario_id}"),
            "creado_en": c.creado_en,
        }
        for c in comentarios
    ]


def agregar_comentario(session: Session, entidad_tipo: str, entidad_id: int, usuario_id: int, texto: str) -> Comentario:
    comentario = Comentario(
        entidad_tipo=entidad_tipo, entidad_id=entidad_id, usuario_id=usuario_id, texto=texto.strip(),
    )
    session.add(comentario)
    return comentario
