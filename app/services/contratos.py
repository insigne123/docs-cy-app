"""Casos de uso de contratos (Línea A y B)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.enums import (
    CategoriaContrato,
    EntidadTipo,
    EstadoContrato,
    LineaContrato,
    Moneda,
    Rol,
)
from app.models.contrato import Contrato
from app.models.core import Contraparte, FormatoEstandar, Unidad, Usuario
from app.models.evento import EventoEstado
from app.services.parametros import obtener_parametro


def calcular_requiere_gerencia(
    session: Session,
    monto: Optional[Decimal],
    moneda: Optional[Moneda],
    monto_referencia_clp: Optional[Decimal],
) -> bool:
    umbral = Decimal(str(obtener_parametro(session, "monto_aprobacion_gerencia_clp", "50000000")))
    base: Optional[Decimal] = None
    if monto_referencia_clp is not None:
        base = Decimal(str(monto_referencia_clp))
    elif monto is not None and moneda == Moneda.CLP:
        base = Decimal(str(monto))
    return base is not None and base >= umbral


def crear_contrato(
    session: Session,
    *,
    codigo: str,
    linea: LineaContrato,
    objeto: str,
    unidad_solicitante: Unidad,
    solicitante: Usuario,
    contraparte: Optional[Contraparte] = None,
    formato: Optional[FormatoEstandar] = None,
    categoria: Optional[CategoriaContrato] = None,
    monto: Optional[Decimal] = None,
    moneda: Optional[Moneda] = None,
    monto_referencia_clp: Optional[Decimal] = None,
    requiere_garantia: bool = False,
    requiere_visacion_contraparte: bool = False,
    fecha_ingreso: Optional[date] = None,
) -> Contrato:
    """Crea un contrato en estado 'ingreso' y registra el primer evento de trazabilidad."""
    if linea == LineaContrato.B_autogestionado and formato is None:
        raise ValueError("La Línea B (autogestionado) requiere un formato estándar")
    if linea == LineaContrato.C_licitacion:
        raise ValueError("Los contratos de Línea C se crean vía adjudicación de una licitación")

    contrato = Contrato(
        codigo=codigo,
        linea=linea,
        objeto=objeto,
        categoria=categoria,
        unidad_solicitante_id=unidad_solicitante.id,
        solicitante_id=solicitante.id,
        contraparte_id=contraparte.id if contraparte else None,
        formato_id=formato.id if formato else None,
        estado=EstadoContrato.ingreso,
        estado_desde=datetime.utcnow(),
        requiere_aprobacion_gerencia=calcular_requiere_gerencia(session, monto, moneda, monto_referencia_clp),
        requiere_garantia=requiere_garantia,
        requiere_visacion_contraparte=requiere_visacion_contraparte,
        monto=monto,
        moneda=moneda,
        monto_referencia_clp=monto_referencia_clp,
        fecha_ingreso=fecha_ingreso or date.today(),
    )
    session.add(contrato)
    session.flush()

    session.add(
        EventoEstado(
            entidad_tipo=EntidadTipo.contrato.value,
            entidad_id=contrato.id,
            estado_origen=None,
            estado_destino=EstadoContrato.ingreso.value,
            fecha=datetime.utcnow(),
            usuario_id=solicitante.id,
            rol_actor=Rol.unidad_solicitante.value,
            comentario="Ingreso de solicitud",
        )
    )
    session.flush()
    return contrato
