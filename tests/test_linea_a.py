"""Línea A — Flujo Regular / Abastecimiento."""
from __future__ import annotations

from datetime import date

import pytest

from app.enums import EstadoContrato, LineaContrato, Moneda, Rol
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados, RolNoAutorizado
from tests._helpers import avanzar_a, crear_contrato_a


def test_flujo_a_completo(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte, codigo="CT-2026-0001")
    session.commit()
    motor = MotorEstados(session)

    avanzar_a(motor, c, usuarios, EstadoContrato.vigente)
    session.commit()

    assert c.estado == EstadoContrato.vigente
    destinos = [e.estado_destino for e in motor.historial(c)]
    assert destinos == [
        "ingreso",
        "aprobacion_jefatura",
        "admisibilidad_1",
        "admisibilidad_2",
        "elaboracion",
        "visacion",
        "firma",
        "integracion",
        "vigente",
    ]
    assert c.fecha_aprobacion_jefatura is not None
    assert c.fecha_firma is not None
    assert c.fecha_integracion is not None
    # ef_iniciar_vigencia deja un hito de inicio de ejecución
    assert any(h.tipo.value == "inicio_ejecucion" for h in c.hitos)


def test_a_con_aprobacion_gerencia_por_monto(session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session,
        codigo="CT-2026-0010",
        linea=LineaContrato.A_regular,
        objeto="Contrato de alto monto",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte,
        monto=90_000_000,
        moneda=Moneda.CLP,
    )
    session.commit()
    assert c.requiere_aprobacion_gerencia is True

    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])
    # No puede saltarse a Gerencia si el rol no corresponde
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_gerencia, usuario=usuarios[Rol.jefatura])
    assert c.estado == EstadoContrato.aprobacion_gerencia
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.gerencia])
    assert c.estado == EstadoContrato.admisibilidad_1
    session.commit()


def test_a_monto_bajo_no_pasa_por_gerencia(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte, monto=1_000_000)
    session.commit()
    assert c.requiere_aprobacion_gerencia is False

    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])
    from app.state_machine import PrecondicionNoCumplida

    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.aprobacion_gerencia, usuario=usuarios[Rol.jefatura])


def test_a_rol_incorrecto_es_rechazado(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])
    # admisibilidad_1 -> admisibilidad_2 es competencia de Legal, no de Jefatura
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.jefatura])
    with pytest.raises(RolNoAutorizado):
        motor.transicionar_contrato(c, EstadoContrato.admisibilidad_2, usuario=usuarios[Rol.jefatura])
