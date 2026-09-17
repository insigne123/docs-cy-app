"""Trazabilidad: cada transición deja un evento con quién, cuándo, de/a y comentario."""
from __future__ import annotations

from app.enums import EstadoContrato, Rol
from app.models.evento import EventoEstado
from app.state_machine import MotorEstados
from tests._helpers import avanzar_a, crear_contrato_a


def test_historial_ordenado_y_completo(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.vigente)
    session.commit()

    hist = motor.historial(c)
    # 1 evento de creación + 8 transiciones de Línea A
    assert len(hist) == 9
    assert hist[0].estado_origen is None
    assert hist[0].estado_destino == "ingreso"
    # encadenamiento origen/destino consistente
    for previo, actual in zip(hist, hist[1:]):
        assert actual.estado_origen == previo.estado_destino
    for e in hist:
        assert e.usuario_id is not None
        assert e.rol_actor
        assert e.fecha is not None


def test_evento_guarda_comentario_y_rol(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.admisibilidad_1)
    motor.transicionar_contrato(
        c, EstadoContrato.aclaraciones, usuario=usuarios[Rol.legal], comentario="Falta información"
    )
    session.commit()

    ev = motor.historial(c)[-1]
    assert ev.estado_destino == "aclaraciones"
    assert ev.rol_actor == Rol.legal.value
    assert ev.comentario == "Falta información"
    assert ev.retorno_a == EstadoContrato.admisibilidad_1.value


def test_transiciones_de_dos_expedientes_no_se_mezclan(session, usuarios, unidad, contraparte):
    motor = MotorEstados(session)
    c1 = crear_contrato_a(session, usuarios, unidad, contraparte, codigo="CT-A-1")
    c2 = crear_contrato_a(session, usuarios, unidad, contraparte, codigo="CT-A-2")
    session.commit()
    avanzar_a(motor, c1, usuarios, EstadoContrato.admisibilidad_1)
    avanzar_a(motor, c2, usuarios, EstadoContrato.aprobacion_jefatura)
    session.commit()

    assert {e.entidad_id for e in motor.historial(c1)} == {c1.id}
    assert {e.entidad_id for e in motor.historial(c2)} == {c2.id}
    assert session.query(EventoEstado).filter_by(entidad_id=c1.id).count() == 3
    assert session.query(EventoEstado).filter_by(entidad_id=c2.id).count() == 2
