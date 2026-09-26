"""Bandeja de tareas: contratos y licitaciones donde el usuario logueado
puede actuar ahora mismo, según su rol y el estado actual de cada uno.

Reutiliza las mismas tablas de transiciones que usa el motor de estados
(app/state_machine/transitions.py), así que se mantiene sincronizada con
las reglas de rol reales sin duplicarlas.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import (
    ESTADOS_CONTRATO_TERMINALES,
    ESTADOS_LICITACION_TERMINALES,
    nombre_linea,
)
from app.models.contrato import Contrato
from app.models.core import Contraparte, Usuario
from app.models.licitacion import Licitacion
from app.state_machine.transitions import TRANSICIONES_CONTRATO, TRANSICIONES_LICITACION

_TERM_CONTRATO = frozenset(e.value for e in ESTADOS_CONTRATO_TERMINALES)
_TERM_LICITACION = frozenset(e.value for e in ESTADOS_LICITACION_TERMINALES)


def _puede_actuar_contrato(rol_val: str, estado: str, linea_val: str) -> bool:
    return any(
        t.desde == estado and rol_val in t.roles and (not t.lineas or linea_val in t.lineas)
        for t in TRANSICIONES_CONTRATO
    )


def _puede_actuar_licitacion(rol_val: str, estado: str) -> bool:
    return any(t.desde == estado and rol_val in t.roles for t in TRANSICIONES_LICITACION)


def tareas_pendientes(session: Session, usuario: Usuario) -> dict:
    """admin_sistema solo ve tareas en 'ingreso' (es el único punto donde ese
    rol aparece como bypass técnico en las transiciones, no como rol de
    negocio) — igual que cualquier otro rol, se limita a lo que las
    transiciones realmente le permiten ejecutar."""
    rol_val = usuario.rol.value
    nombres_cp = {c.id: c.razon_social for c in session.scalars(select(Contraparte))}

    contratos = []
    for c in session.scalars(select(Contrato).order_by(Contrato.fecha_ingreso)):
        if c.estado.value in _TERM_CONTRATO:
            continue
        if _puede_actuar_contrato(rol_val, c.estado.value, c.linea.value):
            contratos.append({
                "id": c.id,
                "codigo": c.codigo,
                "objeto": c.objeto,
                "estado": c.estado.value,
                "linea": c.linea.value,
                "linea_nombre": nombre_linea(c.linea.value),
                "contraparte": nombres_cp.get(c.contraparte_id),
                "fecha_ingreso": c.fecha_ingreso,
            })

    licitaciones = []
    for l in session.scalars(select(Licitacion).order_by(Licitacion.fecha_ingreso)):
        if l.estado.value in _TERM_LICITACION:
            continue
        if _puede_actuar_licitacion(rol_val, l.estado.value):
            licitaciones.append({
                "id": l.id,
                "codigo": l.codigo,
                "objeto": l.objeto,
                "estado": l.estado.value,
                "fecha_ingreso": l.fecha_ingreso,
            })

    return {
        "contratos": contratos,
        "licitaciones": licitaciones,
        "total": len(contratos) + len(licitaciones),
    }
