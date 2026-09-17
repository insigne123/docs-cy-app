"""Estado transversal 'aclaraciones': ida y vuelta al estado guardado en retorno_a."""
from __future__ import annotations

import pytest

from app.enums import EstadoContrato, Rol
from app.state_machine import MotorEstados, TransicionNoPermitida
from tests._helpers import avanzar_a, crear_contrato_a


def test_aclaraciones_ida_y_vuelta(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.admisibilidad_1)

    motor.transicionar_contrato(
        c, EstadoContrato.aclaraciones, usuario=usuarios[Rol.legal],
        comentario="Falta anexo técnico",
    )
    assert c.estado == EstadoContrato.aclaraciones
    assert c.retorno_a == EstadoContrato.admisibilidad_1.value

    # No se puede saltar a otro estado desde aclaraciones
    with pytest.raises(TransicionNoPermitida):
        motor.transicionar_contrato(c, EstadoContrato.admisibilidad_2, usuario=usuarios[Rol.unidad_solicitante])

    motor.transicionar_contrato(
        c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.unidad_solicitante],
        comentario="Anexo adjuntado",
    )
    session.commit()

    assert c.estado == EstadoContrato.admisibilidad_1
    assert c.retorno_a is None
    destinos = [e.estado_destino for e in motor.historial(c)]
    assert destinos.count("admisibilidad_1") == 2
    assert "aclaraciones" in destinos


def test_aclaraciones_desde_elaboracion(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.elaboracion)

    motor.transicionar_contrato(
        c, EstadoContrato.aclaraciones, usuario=usuarios[Rol.legal], comentario="Consulta al solicitante"
    )
    assert c.retorno_a == EstadoContrato.elaboracion.value
    motor.transicionar_contrato(c, EstadoContrato.elaboracion, usuario=usuarios[Rol.unidad_solicitante])
    assert c.estado == EstadoContrato.elaboracion
    assert c.retorno_a is None
