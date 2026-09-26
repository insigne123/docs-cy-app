"""Búsqueda global rápida: contratos y licitaciones por código, objeto o
nombre de la contraparte."""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.enums import nombre_linea
from app.models.contrato import Contrato
from app.models.core import Contraparte
from app.models.licitacion import Licitacion

LIMITE = 25


def buscar_global(session: Session, q: str) -> dict:
    q = (q or "").strip()
    if not q:
        return {"q": q, "contratos": [], "licitaciones": []}
    patron = f"%{q}%"

    ids_contraparte = list(
        session.scalars(select(Contraparte.id).where(Contraparte.razon_social.ilike(patron)))
    )
    condiciones_contrato = [Contrato.codigo.ilike(patron), Contrato.objeto.ilike(patron)]
    if ids_contraparte:
        condiciones_contrato.append(Contrato.contraparte_id.in_(ids_contraparte))

    nombres_cp = {c.id: c.razon_social for c in session.scalars(select(Contraparte))}
    contratos = [
        {
            "id": c.id,
            "codigo": c.codigo,
            "objeto": c.objeto,
            "linea": c.linea.value,
            "linea_nombre": nombre_linea(c.linea.value),
            "estado": c.estado.value,
            "contraparte": nombres_cp.get(c.contraparte_id),
        }
        for c in session.scalars(
            select(Contrato).where(or_(*condiciones_contrato)).order_by(Contrato.codigo).limit(LIMITE)
        )
    ]

    licitaciones = [
        {"id": l.id, "codigo": l.codigo, "objeto": l.objeto, "estado": l.estado.value}
        for l in session.scalars(
            select(Licitacion)
            .where(or_(Licitacion.codigo.ilike(patron), Licitacion.objeto.ilike(patron)))
            .order_by(Licitacion.codigo)
            .limit(LIMITE)
        )
    ]

    return {"q": q, "contratos": contratos, "licitaciones": licitaciones}
