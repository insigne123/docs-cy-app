"""Casos de uso de licitaciones (Línea C)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.enums import (
    EntidadTipo,
    EstadoContrato,
    EstadoLicitacion,
    LicitacionFase,
    LineaContrato,
    Moneda,
)
from app.models.contrato import Contrato
from app.models.core import Contraparte, Unidad, Usuario
from app.models.evento import EventoEstado
from app.models.licitacion import Licitacion
from app.state_machine.engine import MotorEstados


def crear_licitacion(
    session: Session,
    *,
    codigo: str,
    objeto: str,
    unidad_solicitante: Unidad,
    solicitante: Usuario,
    contraparte: Optional[Contraparte] = None,
    mandante: Optional[str] = None,
    moneda: Optional[Moneda] = None,
    exige_garantia_seriedad: bool = False,
    fecha_ingreso: Optional[date] = None,
) -> Licitacion:
    """Crea una licitación en estado 'ingreso_antecedentes' y registra el primer evento."""
    lic = Licitacion(
        codigo=codigo,
        objeto=objeto,
        mandante=mandante,
        contraparte_id=contraparte.id if contraparte else None,
        unidad_solicitante_id=unidad_solicitante.id,
        fase=LicitacionFase.pre_adjudicacion,
        estado=EstadoLicitacion.ingreso_antecedentes,
        moneda=moneda,
        exige_garantia_seriedad=exige_garantia_seriedad,
        fecha_ingreso=fecha_ingreso or date.today(),
    )
    session.add(lic)
    session.flush()

    session.add(
        EventoEstado(
            entidad_tipo=EntidadTipo.licitacion.value,
            entidad_id=lic.id,
            estado_origen=None,
            estado_destino=EstadoLicitacion.ingreso_antecedentes.value,
            fecha=datetime.utcnow(),
            usuario_id=solicitante.id,
            rol_actor=solicitante.rol.value,
            comentario="Ingreso de antecedentes de licitación",
        )
    )
    session.flush()
    return lic


def adjudicar_licitacion(
    session: Session,
    licitacion: Licitacion,
    *,
    usuario: Usuario,
    codigo_contrato: str,
    objeto: Optional[str] = None,
    contraparte: Optional[Contraparte] = None,
    comentario: str = "Adjudicación de la licitación",
) -> Contrato:
    """Mueve la licitación a 'adjudicada' y crea el contrato de Línea C en 'formalizacion_ajuste'."""
    motor = MotorEstados(session)
    motor.transicionar_licitacion(
        licitacion, EstadoLicitacion.adjudicada, usuario=usuario, comentario=comentario
    )
    licitacion.fase = LicitacionFase.formalizacion

    contrato = Contrato(
        codigo=codigo_contrato,
        linea=LineaContrato.C_licitacion,
        objeto=objeto or licitacion.objeto,
        unidad_solicitante_id=licitacion.unidad_solicitante_id,
        solicitante_id=usuario.id,
        contraparte_id=(contraparte.id if contraparte else licitacion.contraparte_id),
        licitacion_id=licitacion.id,
        estado=EstadoContrato.formalizacion_ajuste,
        estado_desde=datetime.utcnow(),
        moneda=licitacion.moneda,
        fecha_ingreso=date.today(),
    )
    session.add(contrato)
    session.flush()

    licitacion.contrato_id = contrato.id

    session.add(
        EventoEstado(
            entidad_tipo=EntidadTipo.contrato.value,
            entidad_id=contrato.id,
            estado_origen=None,
            estado_destino=EstadoContrato.formalizacion_ajuste.value,
            fecha=datetime.utcnow(),
            usuario_id=usuario.id,
            rol_actor=usuario.rol.value,
            comentario=f"Contrato creado por adjudicación de {licitacion.codigo}",
        )
    )
    session.flush()
    return contrato
