"""Línea B — Flujo Express / Autogestionado."""
from __future__ import annotations

import pytest

from app.enums import EstadoContrato, LineaContrato, Moneda, Rol
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados, PrecondicionNoCumplida, TransicionNoPermitida


def _crear_b(session, usuarios, unidad, contraparte, formato, monto=500_000):
    return crear_contrato(
        session,
        codigo="CT-2026-0002",
        linea=LineaContrato.B_autogestionado,
        objeto="NDA proveedor",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte,
        formato=formato,
        monto=monto,
        moneda=Moneda.CLP,
    )


def test_flujo_b_completo_sin_elaboracion(session, usuarios, unidad, contraparte, formato):
    c = _crear_b(session, usuarios, unidad, contraparte, formato)
    session.commit()
    motor = MotorEstados(session)

    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.unidad_solicitante])
    motor.transicionar_contrato(
        c, EstadoContrato.visacion, usuario=usuarios[Rol.legal], extra={"documento_checksum": "abc123"}
    )
    motor.transicionar_contrato(c, EstadoContrato.firma, usuario=usuarios[Rol.legal])
    motor.transicionar_contrato(
        c, EstadoContrato.integracion, usuario=usuarios[Rol.legal], extra={"documento_firmado": True}
    )
    c.administrador_id = usuarios[Rol.admin_contratos].id
    c.vigencia_indefinida = True
    motor.transicionar_contrato(c, EstadoContrato.vigente, usuario=usuarios[Rol.admin_contratos])
    session.commit()

    destinos = [e.estado_destino for e in motor.historial(c)]
    assert destinos == ["ingreso", "admisibilidad_1", "visacion", "firma", "integracion", "vigente"]
    assert "elaboracion" not in destinos
    assert "aprobacion_jefatura" not in destinos


def test_b_no_admite_estado_elaboracion(session, usuarios, unidad, contraparte, formato):
    c = _crear_b(session, usuarios, unidad, contraparte, formato)
    session.commit()
    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.unidad_solicitante])
    with pytest.raises(TransicionNoPermitida):
        motor.transicionar_contrato(c, EstadoContrato.elaboracion, usuario=usuarios[Rol.legal])


def test_b_formato_modificado_es_rechazado(session, usuarios, unidad, contraparte, formato):
    c = _crear_b(session, usuarios, unidad, contraparte, formato)
    session.commit()
    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.unidad_solicitante])
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(
            c, EstadoContrato.visacion, usuario=usuarios[Rol.legal],
            extra={"documento_checksum": "CHECKSUM-DISTINTO"},
        )
    # Sin checksum tampoco avanza
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.visacion, usuario=usuarios[Rol.legal])


def test_b_alto_monto_pasa_por_gerencia(session, usuarios, unidad, contraparte, formato):
    c = _crear_b(session, usuarios, unidad, contraparte, formato, monto=90_000_000)
    session.commit()
    assert c.requiere_aprobacion_gerencia is True
    motor = MotorEstados(session)
    # con monto alto, ingreso -> admisibilidad_1 directo NO está permitido
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.unidad_solicitante])
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_gerencia, usuario=usuarios[Rol.unidad_solicitante])
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.gerencia])
    assert c.estado == EstadoContrato.admisibilidad_1
