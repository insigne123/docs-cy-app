"""Estado transversal 'descartado': cierre definitivo desde cualquier estado no terminal."""
from __future__ import annotations

from datetime import date

import pytest

from app.enums import EstadoContrato, EstadoLicitacion, Rol
from app.services.licitaciones import crear_licitacion
from app.state_machine import MotorEstados, PrecondicionNoCumplida, TransicionNoPermitida
from tests._helpers import avanzar_a, crear_contrato_a


def test_descartar_contrato_a_mitad_de_flujo(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.elaboracion)

    motor.transicionar_contrato(
        c, EstadoContrato.descartado, usuario=usuarios[Rol.legal],
        comentario="Inviabilidad legal detectada en la redacción",
    )
    session.commit()

    assert c.estado == EstadoContrato.descartado
    assert c.motivo_descarte == "Inviabilidad legal detectada en la redacción"
    assert c.fecha_cierre is not None
    assert motor.historial(c)[-1].estado_destino == "descartado"


def test_descartado_es_terminal(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    motor.transicionar_contrato(
        c, EstadoContrato.descartado, usuario=usuarios[Rol.unidad_solicitante], comentario="Ya no se requiere"
    )
    with pytest.raises(TransicionNoPermitida):
        motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])


def test_descarte_requiere_motivo(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.descartado, usuario=usuarios[Rol.legal])


def test_descartar_licitacion(session, usuarios, unidad):
    motor = MotorEstados(session)
    lic = crear_licitacion(
        session, codigo="LIC-2026-0009", objeto="Proyecto X",
        unidad_solicitante=unidad, solicitante=usuarios[Rol.admin_licitaciones],
    )
    session.commit()
    motor.transicionar_licitacion(lic, EstadoLicitacion.examen_admisibilidad, usuario=usuarios[Rol.admin_licitaciones])
    motor.transicionar_licitacion(
        lic, EstadoLicitacion.descartado, usuario=usuarios[Rol.gerencia],
        comentario="Proyecto inviable en el examen de admisibilidad",
    )
    session.commit()
    assert lic.estado == EstadoLicitacion.descartado
