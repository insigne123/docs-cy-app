"""Invariantes del motor de estados (docs/02-maquina-de-estados.md §5)."""
from __future__ import annotations

from datetime import date

import pytest

from app.enums import (
    EstadoContrato,
    GarantiaEstado,
    GarantiaInstrumento,
    GarantiaTipo,
    LineaContrato,
    Moneda,
    Rol,
)
from app.models.contrato import Garantia
from app.services.contratos import crear_contrato
from app.state_machine import MotorEstados, PrecondicionNoCumplida
from tests._helpers import avanzar_a, crear_contrato_a


def test_elaboracion_exige_abogado_asignado(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    motor.transicionar_contrato(c, EstadoContrato.aprobacion_jefatura, usuario=usuarios[Rol.unidad_solicitante])
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_1, usuario=usuarios[Rol.jefatura])
    motor.transicionar_contrato(c, EstadoContrato.admisibilidad_2, usuario=usuarios[Rol.legal])
    # sin abogado_id -> se rechaza
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.elaboracion, usuario=usuarios[Rol.legal])
    c.abogado_id = usuarios[Rol.legal].id
    motor.transicionar_contrato(c, EstadoContrato.elaboracion, usuario=usuarios[Rol.legal])
    assert c.estado == EstadoContrato.elaboracion


def test_pasar_a_vigente_exige_administrador_y_vigencia(session, usuarios, unidad, contraparte):
    c = crear_contrato_a(session, usuarios, unidad, contraparte)
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.integracion)

    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.vigente, usuario=usuarios[Rol.admin_contratos])

    c.administrador_id = usuarios[Rol.admin_contratos].id
    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.vigente, usuario=usuarios[Rol.admin_contratos])

    c.fecha_fin_vigencia = date(2030, 1, 1)
    motor.transicionar_contrato(c, EstadoContrato.vigente, usuario=usuarios[Rol.admin_contratos])
    assert c.estado == EstadoContrato.vigente


def test_firma_exige_garantia_cuando_requiere_garantia(session, usuarios, unidad, contraparte):
    c = crear_contrato(
        session,
        codigo="CT-2026-0050",
        linea=LineaContrato.A_regular,
        objeto="Contrato con garantía",
        unidad_solicitante=unidad,
        solicitante=usuarios[Rol.unidad_solicitante],
        contraparte=contraparte,
        monto=1_000_000,
        moneda=Moneda.CLP,
        requiere_garantia=True,
    )
    session.commit()
    motor = MotorEstados(session)
    avanzar_a(motor, c, usuarios, EstadoContrato.visacion)

    with pytest.raises(PrecondicionNoCumplida):
        motor.transicionar_contrato(c, EstadoContrato.firma, usuario=usuarios[Rol.legal])

    session.add(
        Garantia(
            entidad_tipo="contrato",
            entidad_id=c.id,
            tipo=GarantiaTipo.fiel_cumplimiento,
            instrumento=GarantiaInstrumento.boleta_bancaria,
            monto=100_000,
            moneda=Moneda.CLP,
            fecha_emision=date(2026, 1, 1),
            fecha_vencimiento=date(2027, 1, 1),
            estado=GarantiaEstado.vigente,
        )
    )
    session.flush()
    motor.transicionar_contrato(c, EstadoContrato.firma, usuario=usuarios[Rol.legal])
    assert c.estado == EstadoContrato.firma
